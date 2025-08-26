# Mini Crafter

A compact and efficient reinforcement learning environment based on the original Crafter, designed for faster research and experimentation.

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
