# MiniCrafter

A compact and efficient reinforcement learning environment based on the original Crafter, designed for faster research and experimentation.


<table>
  <tr>
    <td align="center">
      <video src="https://github.com/user-attachments/assets/e14cac40-3288-4c66-85b8-d8bebfe59207" width="300" controls></video><br>
      <b>MDP gameplay</b>
    </td>
    <td align="center">
      <video src="https://github.com/user-attachments/assets/f85b5a02-ed70-4a5a-bd83-2462052eb46a" width="300" controls></video><br>
      <b>POMDP gameplay</b>
    </td>
  </tr>
</table>



## Key Features

- **Two Modes:**
  - **MDP Mode:** 9x9 fully observable world.
  - **POMDP Mode:** 15x15 partially observable world.
- **Peaceful Mode:** Play without hostile creatures.
- **Simple GUI Launcher:** An easy way to start playing.
- **Crafter Compatible:** A drop-in replacement for the original `crafter` environment.
- **Record Gameplay:** Save videos of your gameplay sessions.

## Installation

Install the required packages with:

```bash
pip install -r requirements.txt
```

## How to Play

Run the interactive launcher from the `mini_crafter_v2` directory:

```bash
python play_mini_crafter_gui.py
```

This will present a menu to choose your desired game mode.

## Controls

- **WASD:** Move
- **Space:** Interact / Use Tool
- **Tab:** Sleep
- **R/T/F/P:** Place Stone / Table / Furnace / Plant
- **1-6:** Craft Tools
- **ESC:** Quit

## Programmatic Usage

```python
import mini_crafter

# MDP mode (fully observable)
env = mini_crafter.Env(mode='mdp')

# POMDP mode (partially observable)
env = mini_crafter.Env(mode='pomdp')

obs = env.reset()
obs, reward, done, info = env.step(env.action_space.sample())
```
