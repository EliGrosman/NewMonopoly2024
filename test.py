num_episodes_train = 200
num_episodes_test = 20
learning_rate = 5e-4

from env import MonopolyEnv
import numpy as np
from tqdm import tqdm
from agent import DQN_Agent
import matplotlib.pyplot as plt
# Create the environment
env = MonopolyEnv()
action_space_size = env.as_size
state_space_size = env.output_shape

# Plot average performance of 5 trials
num_seeds = 5
l = num_episodes_train // 10
res = np.zeros((num_seeds, l))
gamma = 0.99
train_losses = []
# Loop over multiple seeds
for i in tqdm(range(num_seeds)):
    reward_means = []
    # Create an instance of the DQN_Agent class
    agent = DQN_Agent(env, lr=learning_rate)

    # Training loop
    for m in range(num_episodes_train):
        train_loss = agent.train()
        train_losses.append(train_loss)

        # Evaluate the agent every 10 episodes during training
        if m % 10 == 0:
            # print("Episode: {}".format(m))

            # Evaluate the agent's performance over 20 test episodes
            G = np.zeros(num_episodes_test)
            for k in range(num_episodes_test):
                g = agent.test()
                G[k] = g

            reward_mean = G.mean()
            reward_sd = G.std()
            # print(f"The test reward for episode {m} is {reward_mean} with a standard deviation of {reward_sd}.")
            reward_means.append(reward_mean)

    res[i] = np.array(reward_means)

# Plotting the average performance
ks = list(range(num_episodes_train*num_seeds))
maxs = np.max(train_losses, axis=0)
mins = np.min(train_losses, axis=0)

plt.fill_between(ks, mins, maxs, alpha=0.1)
plt.plot(ks, train_losses, '-o', markersize=1)

plt.xlabel('Episode', fontsize=15)
plt.ylabel('Avg. Loss', fontsize=15)
plt.savefig('metrics.png')