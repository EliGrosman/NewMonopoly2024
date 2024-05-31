from main import game as monopoly
from gymnasium import Env, spaces
import numpy as np

class MonopolyEnv(Env):
    def __init__(self):
        super(MonopolyEnv, self).__init__()
        game = monopoly()


        self.as_size = len(game.getActionSpace(0))
        self.action_space = spaces.Discrete(len(game.getActionSpace(0)))

        # Define observation space
        self.output_shape = (len(game.getCurrentState(0)),)
        self.observation_space = spaces.Box(low=0, high=10000, shape=self.output_shape, dtype=np.uint8)

    def render(self):
        return None

    def reset(self):
        self.game = monopoly()
        return self.game.getCurrentState(0)

    def step(self, action):
        player_in_step = self.game.current_player
        winner_if_bankrupt = None
        if self.game.current_player is not self.game.last_player:
            winner_if_bankrupt = self.game.env_roll(self.game.players[player_in_step])
            self.game.last_player = self.game.current_player

        return self.game.step(action, winner_if_bankrupt)

    def close(self):
        super().close()
