import collections
import numpy as np

from . import constants
from . import objects

MIN = {
    'wood': 8,
    'water': 1,
    'zombie': 1,
    'skeleton': 1,
    'diamond': 1,
    'stone': 7,
    'coal': 2,
    'iron': 2,
    'grass': 10,
    'sand': 2,
}

T_WATER, T_GRASS, T_STONE, T_SAND = 1, 2, 3, 4
O_NONE, O_TREE, O_COW, O_ZOMBIE, O_SKELETON, O_COAL, O_IRON, O_DIAMOND = 0, 1, 2, 3, 4, 5, 6, 7


def generate_world(world, player, peaceful=False):
    rng = world.random
    attempt = 0
    while True:
        attempt += 1
        grid, overlay = _generate_candidate(world.area, rng, peaceful, attempt, player.pos)
        if grid is None:
            continue
        if _meets_minima_effective(grid, overlay, peaceful) and _spawn_open_enough(grid, overlay, world.area, player.pos, rng):
            _apply_layout(world, player, grid, overlay, peaceful)
            return

def _generate_candidate(world_area, rng, peaceful, attempt, spawn):
    W, H = world_area
    A = W * H
    sx, sy = int(spawn[0]), int(spawn[1])

    grid = np.zeros(world_area, dtype=np.uint8)
    overlay = np.zeros(world_area, dtype=np.uint8)

    # ---- 1) Random base terrain via multi-blob growth + smoothing ----
    # Slight bias to make minima likely even on tiny maps
    water_pct_lo, water_pct_hi = 0.04, 0.10
    stone_pct_lo, stone_pct_hi = 0.22, 0.34

    water_target = max(MIN['water'], int(A * (water_pct_lo + (water_pct_hi - water_pct_lo) * rng.random())))
    stone_target = max(MIN['stone'], int(A * (stone_pct_lo + (stone_pct_hi - stone_pct_lo) * rng.random())))

    # Tiny nudges upward on repeated attempts improve acceptance
    water_target += min(attempt // 15, 2)
    stone_target += min(attempt // 10, 3)

    any_cell  = lambda p: True
    not_water = lambda p: grid[p] != T_WATER

    max_water_blobs = 1 if A <= 100 else 2
    max_stone_blobs = 1 if A <= 100 else 2

    w_cells = _multi_blob_growth(grid, world_area, rng, any_cell, water_target, max_water_blobs)
    for x, y in w_cells:
        grid[x, y] = T_WATER

    s_cells = _multi_blob_growth(grid, world_area, rng, not_water, stone_target, max_stone_blobs)
    for x, y in s_cells:
        grid[x, y] = T_STONE

    # Fill remainder with grass
    for x in range(W):
        for y in range(H):
            if grid[x, y] == 0:
                grid[x, y] = T_GRASS

    # One smoothing pass for organic shapes
    grid = _majority_smooth(grid, world_area)

    # ---- 2) Sand fringe near water (simple) ----
    sand_target = 2 if A <= 100 else 3
    water_adj_grass = []
    for x in range(W):
        for y in range(H):
            if grid[x, y] == T_GRASS and _is_adj(x, y, T_WATER, grid, world_area):
                water_adj_grass.append((x, y))
    if water_adj_grass:
        rng.shuffle(water_adj_grass)
        seed = water_adj_grass[0]
        sand_cells = _bfs_grow(seed, lambda p: grid[p] == T_GRASS, sand_target + rng.randint(0, 2), world_area, rng)
        for x, y in sand_cells:
            grid[x, y] = T_SAND
    else:
        # fallback: sprinkle a couple of sand tiles if no grass touches water
        grass_plots = np.argwhere(grid == T_GRASS)
        if len(grass_plots) > sand_target:
            rng.shuffle(grass_plots)
            for i in range(sand_target):
                grid[tuple(grass_plots[i])] = T_SAND

    # ---- 2.5) Reserve the spawn tile (grass + no overlays) BEFORE capacities ----
    grid[sx, sy] = T_GRASS
    overlay[sx, sy] = O_NONE

    # Quick structural feasibility of base minima *before* baking
    if ((_count(grid, T_GRASS) < MIN['grass']) or
        (_count(grid, T_STONE) < MIN['stone']) or
        (_count(grid, T_WATER) < MIN['water']) or
        (_count(grid, T_SAND)  < MIN['sand'])):
        return None, None

    # ---- 3) Capacity-aware overlays (do not consume reserved base minima) ----
    grass_total = _count(grid, T_GRASS)
    sand_total  = _count(grid, T_SAND)
    stone_total = _count(grid, T_STONE)

    # How many base tiles we can afford to consume via baking:
    grass_cap_for_trees = max(0, grass_total - MIN['grass'])
    sand_cap_for_trees  = max(0, sand_total  - MIN['sand'])
    stone_cap_for_ores  = max(0, stone_total - MIN['stone'])

    # If we cannot put at least the MIN ores into stone without breaking MIN['stone'], abort early
    min_ore_total = MIN['coal'] + MIN['iron'] + MIN['diamond']
    if stone_cap_for_ores < min_ore_total:
        return None, None

    # --- Size-scaled randomness so bigger maps tend to spawn > minima ---
    # 9x7=63, 9x9=81, 15x15=225. area_scale in [0, ~1] for common sizes.
    area_scale = min(1.0, A / 225.0)
    # Random boost factor up to +60% on 15x15, smaller on tiny maps
    boost = 1.0 + 0.6 * area_scale * rng.random()

    # Choose randomized targets (>= minima), then apply boost
    wood_k_raw = int(grass_total * (0.18 + 0.12 * rng.random()))
    coal_k_raw = int(stone_total * (0.08 + 0.08 * rng.random()))
    iron_k_raw = int(stone_total * (0.03 + 0.04 * rng.random()))
    wood_k = max(MIN['wood'], int(wood_k_raw * boost))
    coal_k = max(MIN['coal'], int(coal_k_raw * boost))
    iron_k = max(MIN['iron'], int(iron_k_raw * boost))

    # Diamonds: allow extra on medium/large maps with some randomness
    extra_d = 0
    if A >= 160 and rng.random() < 0.25:  # ~13x13+
        extra_d += 1
    if A >= 256 and rng.random() < 0.15:  # 16x16+
        extra_d += 1
    diam_k = max(1, MIN['diamond'] + extra_d)

    # Clamp ore totals to stone capacity (while keeping minima)
    rem_cap = stone_cap_for_ores
    coal_k = min(coal_k, rem_cap); rem_cap -= coal_k
    iron_k = min(iron_k, rem_cap); rem_cap -= iron_k
    diam_k = min(diam_k, rem_cap); rem_cap -= diam_k

    # After clamping, ensure we still meet minima (safe because rem_cap started >= min_ore_total)
    if coal_k < MIN['coal'] or iron_k < MIN['iron'] or diam_k < MIN['diamond']:
        return None, None

    # Trees can bake on grass or sand; respect each capacity so post-bake grass/sand minima hold.
    # First try to satisfy trees from grass; only then dip into sand.
    max_from_grass = min(wood_k, grass_cap_for_trees)
    wood_rem = wood_k - max_from_grass
    max_from_sand  = min(wood_rem, sand_cap_for_trees)
    wood_from_grass, wood_from_sand = max_from_grass, max_from_sand

    # Ensure we can at least place MIN['wood']
    if (wood_from_grass + wood_from_sand) < MIN['wood']:
        return None, None

    # Candidates (lists are mutated by _place_k). EXCLUDE spawn from all candidates.
    grass_free = [(int(i), int(j)) for (i, j) in np.argwhere((grid == T_GRASS) & (overlay == O_NONE))]
    sand_free  = [(int(i), int(j)) for (i, j) in np.argwhere((grid == T_SAND)  & (overlay == O_NONE))]
    stone_free = [(int(i), int(j)) for (i, j) in np.argwhere((grid == T_STONE) & (overlay == O_NONE))]
    grass_free = [(x, y) for (x, y) in grass_free if not (x == sx and y == sy)]
    sand_free  = [(x, y) for (x, y) in sand_free  if not (x == sx and y == sy)]
    stone_free = [(x, y) for (x, y) in stone_free if not (x == sx and y == sy)]
    walk_free  = list(grass_free) + list(sand_free)

    rng.shuffle(grass_free); rng.shuffle(sand_free); rng.shuffle(stone_free); rng.shuffle(walk_free)

    # Place trees in two phases to respect the per-base capacities
    if wood_from_grass:
        if not _place_k(overlay, O_TREE, wood_from_grass, [grass_free], rng): return None, None
    if wood_from_sand:
        if not _place_k(overlay, O_TREE, wood_from_sand,  [sand_free],  rng): return None, None

    # Ores on stone (stone_free is shrinking as we place)
    if not _place_k(overlay, O_COAL,   coal_k, [stone_free], rng):   return None, None
    if not _place_k(overlay, O_IRON,   iron_k, [stone_free], rng):   return None, None
    if not _place_k(overlay, O_DIAMOND, diam_k, [stone_free], rng):  return None, None

    # Mobs (do not affect post-bake material counts)
    if not peaceful:
        zomb_k = max(MIN['zombie'], 1 + (1 if (A >= 200 and rng.random() < 0.35) else 0))
        skel_k = max(MIN['skeleton'], 1 + (1 if (A >= 200 and rng.random() < 0.35) else 0))
        if not _place_k(overlay, O_ZOMBIE,   zomb_k, [walk_free],  rng): return None, None
        if not _place_k(overlay, O_SKELETON, skel_k, [stone_free], rng): return None, None

    # Final spawn reachability is checked by the caller (_spawn_open_enough)
    return grid, overlay


# --- Acceptance check on effective (post-bake) materials ---

def _meets_minima_effective(grid, overlay, peaceful):
    """Return True iff ALL minima are satisfied in the post-bake world."""
    # Effective base counts exclude tiles that will be baked into resource materials
    grass_eff = int(np.sum((grid == T_GRASS) & (overlay == O_NONE)))  # grass left after tree baking
    sand_eff  = int(np.sum((grid == T_SAND)  & (overlay == O_NONE)))  # sand left after tree baking
    stone_eff = int(np.sum((grid == T_STONE) & (~np.isin(overlay, [O_COAL, O_IRON, O_DIAMOND]))))  # stone left after ores
    water_eff = int(np.sum(grid == T_WATER))

    if grass_eff  < MIN['grass']:  return False
    if sand_eff   < MIN['sand']:   return False
    if stone_eff  < MIN['stone']:  return False
    if water_eff  < MIN['water']:  return False

    # Overlays become materials/objects post-bake
    if int((overlay == O_TREE).sum())    < MIN['wood']:    return False
    if int((overlay == O_COAL).sum())    < MIN['coal']:    return False
    if int((overlay == O_IRON).sum())    < MIN['iron']:    return False
    if int((overlay == O_DIAMOND).sum()) < MIN['diamond']: return False

    if not peaceful:
        if int((overlay == O_ZOMBIE).sum())   < MIN['zombie']:   return False
        if int((overlay == O_SKELETON).sum()) < MIN['skeleton']: return False

    return True


# --- Spawn safety / reachability ---

def _spawn_open_enough(grid, overlay, world_area, spawn, rng):
    """
    Ensure the player is not trapped at spawn.
    We consider walkable post-bake tiles as:
      - base in {GRASS, SAND} AND overlay is not a TREE (trees bake to non-walkable)
    Conditions:
      1) At least one orthogonal neighbor of spawn is walkable
      2) BFS from spawn over walkable tiles reaches at least:
         max(6, 25% of all walkable tiles)
    """
    sx, sy = int(spawn[0]), int(spawn[1])
    W, H = world_area

    def is_walkable(pos):
        return ((grid[pos] == T_GRASS or grid[pos] == T_SAND) and overlay[pos] != O_TREE)

    # 1) Check for at least one open orthogonal neighbor
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    has_exit = False
    for dx, dy in dirs:
        nx, ny = sx + dx, sy + dy
        if 0 <= nx < W and 0 <= ny < H and is_walkable((nx, ny)):
            has_exit = True
            break
    if not has_exit:
        return False

    # 2) BFS reachability on walkable tiles
    reachable = _bfs_grow((sx, sy), lambda p: is_walkable(p), W * H, world_area, rng)
    walkable_total = int(np.sum(((grid == T_GRASS) | (grid == T_SAND)) & (overlay != O_TREE)))

    if walkable_total <= 1:
        return False

    min_reachable = max(6, int(0.25 * walkable_total))
    return len(reachable) >= min_reachable


# --- Helpers ---

def _place_k(overlay, overlay_type, k, cand_lists, rng):
    """Try to place exactly k items using the provided candidate lists (in order)."""
    for _ in range(k):
        placed = False
        for lst in cand_lists:
            while lst:
                # numpy RandomState: randint(0, n) -> [0, n-1]
                i = rng.randint(0, len(lst))  # 0..len(lst)-1
                x, y = lst.pop(i)
                if overlay[x, y] == O_NONE:
                    overlay[x, y] = overlay_type
                    placed = True
                    break
            if placed:
                break
        if not placed:
            return False
    return True


def _bfs_grow(start_node, allowed_check, max_size, world_area, rng):
    q = collections.deque([start_node])
    visited = {start_node}
    while q and len(visited) < max_size:
        x, y = q.popleft()
        neighbors = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
        rng.shuffle(neighbors)
        for nx, ny in neighbors:
            p = (nx, ny)
            if p in visited or not (0 <= nx < world_area[0] and 0 <= ny < world_area[1]):
                continue
            if allowed_check(p):
                visited.add(p)
                q.append(p)
    return visited


def _majority_smooth(grid, world_area):
    new_grid = grid.copy()
    for x in range(world_area[0]):
        for y in range(world_area[1]):
            counts = collections.defaultdict(int)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < world_area[0] and 0 <= ny < world_area[1]:
                        counts[grid[nx, ny]] += 1
            new_grid[x, y] = max(counts, key=counts.get)
    return new_grid


def _is_adj(x, y, tile_type, grid, world_area):
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < world_area[0] and 0 <= ny < world_area[1] and grid[nx, ny] == tile_type:
                return True
    return False


def _count(grid, tile):
    return int((grid == tile).sum())


def _multi_blob_growth(grid, world_area, rng, allowed_check, total_target, max_blobs):
    """
    Grow 1..max_blobs BFS blobs that together reach total_target cells.
    Returns the set of grown cells. Does not mutate grid.
    """
    blobs = 1 if max_blobs <= 1 else (1 + rng.randint(0, max_blobs))  # 1..max_blobs
    budgets = []
    remaining = max(1, total_target)
    for i in range(blobs):
        if i == blobs - 1:
            budgets.append(remaining)
        else:
            avg = max(1, remaining // (blobs - i))
            jitter = rng.randint(-2, 3)  # -2..+2
            part = max(1, min(remaining - (blobs - i - 1), avg + jitter))
            budgets.append(part)
            remaining -= part

    grown = set()
    for b in budgets:
        # pick a random seed that satisfies allowed_check
        tries = 0
        seed = None
        while tries <= 64:
            sx = rng.randint(0, world_area[0])  # 0..W-1
            sy = rng.randint(0, world_area[1])  # 0..H-1
            cand = (sx, sy)
            if allowed_check(cand) and cand not in grown:
                seed = cand
                break
            tries += 1
        if seed is None:
            continue
        used = _bfs_grow(seed, lambda p: allowed_check(p) and p not in grown, b, world_area, rng)
        grown |= used
    return grown


# --- Apply Layout to World ---

def _apply_layout(world, player, grid, overlay, peaceful):
    """Converts grid+overlay into engine world state (no cows)."""
    T_WATER, T_GRASS, T_STONE, T_SAND = 1, 2, 3, 4
    O_NONE, O_TREE, O_COW, O_ZOMBIE, O_SKELETON, O_COAL, O_IRON, O_DIAMOND = 0, 1, 2, 3, 4, 5, 6, 7

    mat_map = {T_WATER: 'water', T_GRASS: 'grass', T_STONE: 'stone', T_SAND: 'sand'}
    overlay_mats = {O_TREE: 'tree', O_COAL: 'coal', O_IRON: 'iron', O_DIAMOND: 'diamond'}

    # Clear existing objects except player
    for obj in list(world.objects):
        if not isinstance(obj, objects.Player):
            world.remove(obj)

    # Write base + baked resources
    for x in range(world.area[0]):
        for y in range(world.area[1]):
            pos = (x, y)
            world[pos] = mat_map.get(grid[x, y], 'grass')
            if overlay[x, y] in overlay_mats:
                world[pos] = overlay_mats[overlay[x, y]]

    # Ensure safe spawn (should already be grass due to reservation)
    if world[player.pos][0] != 'grass':
        world[player.pos] = 'grass'

    # Spawn mobs
    if not peaceful:
        for x in range(world.area[0]):
            for y in range(world.area[1]):
                pos = (x, y)
                # Clear any existing non-player object first
                if world[pos][1] and not isinstance(world[pos][1], objects.Player):
                    world.remove(world[pos][1])
                if overlay[x, y] == O_ZOMBIE:
                    world.add(objects.Zombie(world, pos, player))
                elif overlay[x, y] == O_SKELETON:
                    world.add(objects.Skeleton(world, pos, player))
