import random
import collections
import torch
from stuff import Transition
class ReplayMemory:
    def __init__(self, env, memory_size=50000, burn_in=10000):
        # Initializes the replay memory, which stores transitions recorded from the agent taking actions in the environment.
        self.memory_size = memory_size
        self.burn_in = burn_in
        self.memory = collections.deque([], maxlen=memory_size)
        self.env = env

    def sample_batch(self, batch_size=32):
        # Returns a batch of randomly sampled transitions to be used for training the model.
        return random.sample(self.memory, batch_size)

    def append(self, transition):
        if len(transition.action.shape) == 1:
            transition = Transition(transition.state, torch.reshape(transition.action, (1, transition.action.shape[0])), transition.next_state, transition.reward)
        # Appends a transition to the replay memory.
        self.memory.append(transition)