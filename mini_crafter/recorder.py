import datetime
import json
import pathlib

import imageio
import numpy as np
import gym


class Recorder(gym.Wrapper):

  def __init__(
      self, env, directory, save_stats=True, save_video=True,
      save_episode=True, video_size=(512, 512), fps=30):
    if directory and save_stats:
      env = StatsRecorder(env, directory)
    if directory and save_video:
      env = VideoRecorder(env, directory, video_size, fps=fps)
    if directory and save_episode:
      env = EpisodeRecorder(env, directory)
    super().__init__(env)


class StatsRecorder(gym.Wrapper):

  def __init__(self, env, directory):
    super().__init__(env)
    self._env = env
    self._directory = pathlib.Path(directory).expanduser()
    self._directory.mkdir(exist_ok=True, parents=True)
    self._file = (self._directory / 'stats.jsonl').open('a')
    self._length = None
    self._reward = None
    self._unlocked = None
    self._stats = None

  def reset(self):
    obs = self._env.reset()
    self._length = 0
    self._reward = 0
    self._unlocked = None
    self._stats = None
    return obs

  def step(self, action):
    obs, reward, done, info = self._env.step(action)
    self._length += 1
    self._reward += info['reward']
    if done:
      self._stats = {'length': self._length, 'reward': round(self._reward, 1)}
      for key, value in info['achievements'].items():
        self._stats[f'achievement_{key}'] = value
      self._save()
    return obs, reward, done, info

  def _save(self):
    self._file.write(json.dumps(self._stats) + '\n')
    self._file.flush()


class VideoRecorder(gym.Wrapper):

  def __init__(self, env, directory, size=(512, 512), fps=30):
    super().__init__(env)
    self._env = env
    self._directory = pathlib.Path(directory).expanduser()
    self._directory.mkdir(exist_ok=True, parents=True)
    self._size = size
    self._fps = fps
    self._frames = None

  def reset(self):
    obs = self._env.reset()
    self._frames = [self._env.render(self._size)]
    return obs

  def step(self, action):
    obs, reward, done, info = self._env.step(action)
    self._frames.append(self._env.render(self._size))
    return obs, reward, done, info
  
  def close(self):
    self._save()
    self.env.close()

  def _save(self):
    if not self._frames:
      return
    timestamp = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
    filename = str(self._directory / (timestamp + '.mp4'))
    imageio.mimsave(filename, self._frames, fps=self._fps)


class EpisodeRecorder(gym.Wrapper):

  def __init__(self, env, directory):
    super().__init__(env)
    if not hasattr(env, 'episode_name'):
      env = EpisodeName(env)
    self._env = env
    self._directory = pathlib.Path(directory).expanduser()
    self._directory.mkdir(exist_ok=True, parents=True)
    self._episode = None

  def reset(self):
    obs = self._env.reset()
    self._episode = [{'image': obs}]
    return obs

  def step(self, action):
    # Transitions are defined from the environment perspective, meaning that a
    # transition contains the action and the resulting reward and next
    # observation produced by the environment in response to said action.
    obs, reward, done, info = self._env.step(action)
    transition = {
        'action': action, 'image': obs, 'reward': reward, 'done': done,
    }
    for key, value in info.items():
      if key in ('inventory', 'achievements'):
        continue
      transition[key] = value
    for key, value in info['achievements'].items():
      transition[f'achievement_{key}'] = value
    for key, value in info['inventory'].items():
      transition[f'ainventory_{key}'] = value
    self._episode.append(transition)
    if done:
      self._save()
    return obs, reward, done, info

  def _save(self):
    filename = str(self._directory / (self._env.episode_name + '.npz'))
    # Fill in zeros for keys missing at the first time step.
    for key, value in self._episode[1].items():
      if key not in self._episode[0]:
        self._episode[0][key] = np.zeros_like(value)
    episode = {
        k: np.array([step[k] for step in self._episode])
        for k in self._episode[0]}
    np.savez_compressed(filename, **episode)


class EpisodeName(gym.Wrapper):

  def __init__(self, env):
    super().__init__(env)
    self._env = env
    self._timestamp = None
    self._unlocked = None
    self._length = None

  def reset(self):
    obs = self._env.reset()
    self._timestamp = None
    self._unlocked = None
    self._length = 0
    return obs

  def step(self, action):
    obs, reward, done, info = self._env.step(action)
    self._length += 1
    if done:
      self._timestamp = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
      self._unlocked = sum(int(v >= 1) for v in info['achievements'].values())
    return obs, reward, done, info

  @property
  def episode_name(self):
    return f'{self._timestamp}-ach{self._unlocked}-len{self._length}'
