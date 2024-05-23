
import torch
import numpy as np
import random
from model import QNetwork
from replay import ReplayMemory
from stuff import Transition

class DQN_Agent:

    def __init__(self, env, lr=5e-4, render=False):
        # Initialize the DQN Agent.
        self.env = env
        self.lr = lr
        self.policy_net = QNetwork(self.env, self.lr, self.env.output_shape[0], self.env.as_size)
        self.target_net = QNetwork(self.env, self.lr, self.env.output_shape[0], self.env.as_size)
        self.target_net.net.load_state_dict(self.policy_net.net.state_dict())  # Copy the weight of the policy network
        self.rm = ReplayMemory(self.env)
        self.burn_in_memory()
        self.batch_size = 32
        self.gamma = 0.99
        self.c = 0

    def burn_in_memory(self):
        # Initialize replay memory with a burn-in number of episodes/transitions.
        cnt = 0
        terminated = False
        truncated = False
        state = self.env.reset()
        state = torch.tensor(state, dtype=torch.float32).unsqueeze(0)

        # Iterate until we store "burn_in" buffer
        while cnt < self.rm.burn_in:
            # Reset environment if terminated or truncated
            if terminated or truncated:
                state = self.env.reset()
                state = torch.tensor(state, dtype=torch.float32).unsqueeze(0)

            trueAs = self.env.game.getActionSpace(self.env.game.current_player)
            x, action_mask = self.env.game.print_actionSpace(trueAs)
            random_action_ind = np.random.choice(action_mask, size=1)[0]
            action = [0] * len(trueAs)
            action[random_action_ind] = 1
            action = torch.tensor([action], dtype=torch.long)
            next_state, reward, terminated, info = self.env.step(action)
            reward = torch.tensor([reward])
            if terminated:
                next_state = None
            else:
                next_state = torch.tensor(next_state, dtype=torch.float32).unsqueeze(0)

            # Store new experience into memory
            transition = Transition(state, action, next_state, reward)
            self.rm.append(transition)
            state = next_state
            cnt += 1

    def epsilon_greedy_policy(self, q_values, epsilon=0.05):
        # Implement an epsilon-greedy policy.
        p = random.random()
        trueAs = self.env.game.getActionSpace(self.env.game.current_player)

        x, action_mask = self.env.game.print_actionSpace(trueAs)
        if p > epsilon:
            with torch.no_grad():
                try:
                    if len(trueAs) > 1:
                        as_real = torch.tensor(trueAs)
                    else:
                        as_real = torch.tensor([trueAs])
                    action = self.greedy_policy(q_values, as_real)
                except:
                    print(q_values)
                    print(trueAs)
                    print(q_values*trueAs)
                    import sys
                    sys.exit()
                return torch.reshape(action, (1, len(action)))
        else:
            random_action_ind = np.random.choice(action_mask, size=1)[0]
            action = [0] * len(trueAs)
            action[random_action_ind] = 1
            action = torch.tensor(action, dtype=torch.long)
            return torch.reshape(action, (1, len(action)))

    def greedy_policy(self, q_values, mask):
        # Implement a greedy policy for test time.
        action = torch.tensor([0]*len(mask))
        q_masked = mask * q_values
        action[torch.argmax(q_masked)] = 1
        return action

    def train(self):
        # Train the Q-network using Deep Q-learning.
        state = self.env.reset()
        state = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
        terminated = False
        truncated = False
        all_loss = []

        # Loop until reaching the termination state
        while not (terminated or truncated):
            with torch.no_grad():
                q_values = self.policy_net.net(state)

            # Decide the next action with epsilon greedy strategy
            action = self.epsilon_greedy_policy(q_values)

            # Take action and observe reward and next state
            try:
                next_state, reward, terminated, info = self.env.step(action)
            except:
                print(self.env.game.print_actionSpace(action))
                print(self.env.game.print_state(self.env.game.getCurrentState(self.env.game.current_player)))
            reward = torch.tensor([reward])
            if terminated:
                # print("Game Over")
                # print("Winner: " + info["winner"].name)
                next_state = None
            else:
                next_state = torch.tensor(next_state, dtype=torch.float32).unsqueeze(0)

            # Store the new experience
            transition = Transition(state, action, next_state, reward)
            self.rm.append(transition)

            # Move to the next state
            state = next_state

            # Sample minibatch with size N from memory
            transitions = self.rm.sample_batch(self.batch_size)
            batch = Transition(*zip(*transitions))
            non_final_mask = torch.tensor(tuple(map(lambda s: s is not None, batch.next_state)), dtype=torch.bool)
            non_final_next_states = torch.cat([s for s in batch.next_state if s is not None])
            state_batch = torch.cat(batch.state)

            try:
                action_batch = torch.cat(batch.action)
            except Exception as e:
                raise e
            reward_batch = torch.cat(batch.reward)

            # Get current and next state values
            state_action_values = self.policy_net.net(state_batch).gather(1,
                                                                          action_batch)  # extract values corresponding to the actions Q(S_t, A_t)
            next_state_values = torch.zeros(self.batch_size)

            with torch.no_grad():
                # no next_state_value update if an episode is terminated (next_satate = None)
                # only update the non-termination state values (Ref: https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/)
                next_state_values[non_final_mask] = self.target_net.net(non_final_next_states).max(1)[
                    0]  # extract max value

            # Update the model
            expected_state_action_values = (next_state_values * self.gamma) + reward_batch
            state_action_values = torch.mean(state_action_values, dim=1, keepdims=False)

            if expected_state_action_values.shape != state_action_values.shape:
                print("Exp: " + str(expected_state_action_values.shape))
                print("St: " + str(state_action_values.shape))
            criterion = torch.nn.MSELoss()
            loss = criterion(state_action_values, expected_state_action_values)
            self.policy_net.optimizer.zero_grad()
            loss.backward()
            self.policy_net.optimizer.step()

            all_loss.append(loss.item())

            # Update the target Q-network in each 50 steps
            self.c += 1
            if self.c % 50 == 0:
                self.target_net.net.load_state_dict(self.policy_net.net.state_dict())

        return np.mean(all_loss)
    def test(self, model_file=None):
        # Evaluates the performance of the agent over 20 episodes.

        max_t = 1000
        state = self.env.reset()
        rewards = []

        for t in range(max_t):
            state = torch.from_numpy(state).float().unsqueeze(0)
            with torch.no_grad():
                q_values = self.policy_net.net(state)

            trueAs = self.env.game.getActionSpace(self.env.game.current_player)
            if len(trueAs) > 1:
                as_real = torch.tensor(trueAs)
            else:
                as_real = torch.tensor([trueAs])

            action = self.greedy_policy(q_values, as_real)
            state, reward, terminated, truncated = self.env.step(action)
            rewards.append(reward)
            if terminated or truncated:
                break

        return np.sum(rewards)