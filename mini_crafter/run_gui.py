import argparse

import numpy as np
try:
  import pygame
except ImportError:
  print('Please install the pygame package to use the GUI.')
  raise
from PIL import Image

from . import env as mini_crafter_env
from . import constants


def main():
  boolean = lambda x: bool(['False', 'True'].index(x))
  parser = argparse.ArgumentParser(description='Mini Crafter GUI - Play with keyboard controls')
  parser.add_argument('--seed', type=int, default=None)
  parser.add_argument('--mode', type=str, default='mdp', choices=['mdp', 'pomdp'],
                      help='MDP (9×9 world, fully observable) or POMDP (15×15 world, partially observable)')
  parser.add_argument('--layout', type=str, default='default', choices=['default', 'full'],
                      help='Layout mode: default (9x7 world + inventory) or full (9x9 world + inventory)')
  parser.add_argument('--peaceful', type=boolean, default=True,
                      help='Peaceful mode (no hostile mobs)')
  parser.add_argument('--length', type=int, default=None)
  parser.add_argument('--health', type=int, default=9)
  parser.add_argument('--window', type=int, nargs=2, default=(600, 600))
  parser.add_argument('--size', type=int, nargs=2, default=(0, 0))
  parser.add_argument('--record', type=str, default=None)
  parser.add_argument('--fps', type=int, default=5)
  parser.add_argument('--wait', type=boolean, default=False)
  parser.add_argument('--death', type=str, default='reset', choices=[
      'continue', 'reset', 'quit'])
  parser.add_argument('--worldgen', type=str, default='mini_crafter.worldgen',
                      help='Custom world generation module to use.')
  args = parser.parse_args()

  keymap = {
      pygame.K_a: 'move_left',
      pygame.K_d: 'move_right',
      pygame.K_w: 'move_up',
      pygame.K_s: 'move_down',
      pygame.K_SPACE: 'do',
      pygame.K_TAB: 'sleep',

      pygame.K_r: 'place_stone',
      pygame.K_t: 'place_table',
      pygame.K_f: 'place_furnace',
      pygame.K_p: 'place_plant',

      pygame.K_1: 'make_wood_pickaxe',
      pygame.K_2: 'make_stone_pickaxe',
      pygame.K_3: 'make_iron_pickaxe',
      pygame.K_4: 'make_wood_sword',
      pygame.K_5: 'make_stone_sword',
      pygame.K_6: 'make_iron_sword',
  }
  print('Mini Crafter GUI Controls:')
  for key, action in keymap.items():
    print(f'  {pygame.key.name(key)}: {action}')
  print()

  # Set health configuration
  constants.items['health']['max'] = args.health
  constants.items['health']['initial'] = args.health

  # Configure Mini Crafter environment
  world_size = "9×9" if args.mode == 'mdp' else "15×15"
  observability = "fully observable" if args.mode == 'mdp' else "partially observable"
  
  print(f"Starting Mini Crafter:")
  print(f"  Mode: {args.mode.upper()} ({world_size} world, {observability})")
  if args.mode == 'mdp':
    print(f"  Layout: 9x7 World + 9x2 Inventory (View is 9x9)")
  print(f"  Peaceful: {{'Yes' if args.peaceful else 'No'}}")
  print()

  size = list(args.size)
  size[0] = size[0] or args.window[0]
  size[1] = size[1] or args.window[1]

  # Create Mini Crafter environment with fixed sizes
  env_kwargs = {
      'mode': args.mode,
      'peaceful': args.peaceful,
      'seed': args.seed,
      'worldgen_module': args.worldgen
  }
  
  if args.length is not None:
      env_kwargs['length'] = args.length

  env = mini_crafter_env.Env(**env_kwargs)
  
  # Add recorder if specified
  if args.record:
      from . import recorder
      env = recorder.Recorder(env, args.record)
  
  env.reset()
  achievements = set()
  duration = 0
  return_ = 0
  was_done = False
  print('Diamonds exist:', env.unwrapped._world.count('diamond'))

  pygame.init()
  screen = pygame.display.set_mode(args.window)
  pygame.display.set_caption(f'Mini Crafter - {args.mode.upper()} {world_size} {"Peaceful" if args.peaceful else "Normal"}')
  clock = pygame.time.Clock()
  running = True
  while running:

    # Rendering.
    image = env.render(size)
    if size != args.window:
      image = Image.fromarray(image)
      image = image.resize(args.window, resample=Image.NEAREST)
      image = np.array(image)
    surface = pygame.surfarray.make_surface(image.transpose((1, 0, 2)))
    screen.blit(surface, (0, 0))
    pygame.display.flip()
    clock.tick(args.fps)

    # Keyboard input.
    action = None
    pygame.event.pump()
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False
      elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        running = False
      elif event.type == pygame.KEYDOWN and event.key in keymap.keys():
        action = keymap[event.key]
    if action is None:
      pressed = pygame.key.get_pressed()
      for key, action in keymap.items():
        if pressed[key]:
          break
      else:
        if args.wait and not env.unwrapped._player.sleeping:
          continue
        else:
          action = 'noop'

    # Environment step.
    _, reward, done, info = env.step(env.action_names.index(action))
    duration += 1

    # Achievements.
    unlocked = {
        name for name, count in env.unwrapped._player.achievements.items()
        if count > 0 and name not in achievements}
    for name in unlocked:
      achievements |= unlocked
      total = len(env.unwrapped._player.achievements.keys())
      print(f'Achievement ({len(achievements)}/{total}): {name}')
    if env.unwrapped._step > 0 and env.unwrapped._step % 100 == 0:
      print(f'Time step: {env.unwrapped._step}')
    if reward:
      print(f'Reward: {reward}')
      return_ += reward

    # Episode end.
    if done and not was_done:
      was_done = True
      print('Episode done!')
      print('Duration:', duration)
      print('Return:', return_)
      if args.death == 'quit':
        running = False
      if args.death == 'reset':
        print('\nStarting a new episode.')
        env.reset()
        achievements = set()
        was_done = False
        duration = 0
        return_ = 0
      if args.death == 'continue':
        pass

  env.close()
  pygame.quit()


if __name__ == '__main__':
  main()
