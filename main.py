import msvcrt
import random
import numpy as np
import math

from properties import init_properties
from player import player
from reference import CHANCE_DECK, COMMUNITY_DECK

running = True


class game:
    def __init__(self):
        self.chance_deck = CHANCE_DECK.copy()
        self.community_deck = COMMUNITY_DECK.copy()
        random.shuffle(self.chance_deck)
        random.shuffle(self.community_deck)
        self.c = 1

        self.properties = init_properties(self.chance_deck, self.community_deck, self)

        self.player1 = player("player1", self.properties)
        self.player2 = player("player2", self.properties)
        # self.player3 = player("player3", self.properties)

        # self.player1.buy_ind(12)
        # self.player1.buy_ind(28)

        self.players = [self.player1, self.player2]  # , self.player3]

        self.current_player = 0
        self.last_player = None

    def getCurrentState(self, current_player):
        # 20: player 5x(location, bankrupt, cash, jail flag, has jail card flag)
        # 224?: property. check number. may be 196
        #      28 properties (7dim)
        #         4 owner ()
        #         1 mortgaged flag
        #         1 part of monopoly flag
        #         1 fraction of houses/hotels built
        state = []

        player = self.players[current_player]
        player_order = [player]
        state.append(player.current_location_ind)
        state.append(player.is_bankrupt)
        state.append(player.money)
        state.append(player.jailed)
        # state.append(player.jail_cards > 0)

        for p in range(len(self.players)):
            if p != current_player:
                other_player = self.players[p]
                player_order.append(other_player)
                state.append(other_player.current_location_ind)
                state.append(other_player.is_bankrupt)
                state.append(other_player.money)
                state.append(other_player.jailed)
                # state.append(other_player.jail_cards > 0)

        for property in self.properties:
            if property.type in ["buildable", "railroad", "utility"]:
                new = []
                new.append(1 if property.owner == player_order[0] else 0)
                new.append(1 if property.owner == player_order[1] else 0)
                # state.append(3 if property.owner == player_ids[2] else 0)
                # state.append(4 if property.owner == player_ids[3] else 0)

                new.append(property.mortgaged)
                new.append(1 * property.is_monopoly())
                if property.type == "buildable":
                    new.append((property.houses + 1 * property.hotel) / 5)
                else:
                    new.append(0)
                state += new

        return np.array(state)

    def print_state(self, state):
        for i in range(len(self.players)):
            print(f"Player {i} (in perspective of self)")
            print(f"  - Current location: {state[0+(4*i)]}")
            print(f"  - Is bankrupt: {bool(state[1+(4*i)])}")
            print(f"  - Money: {state[2+(4*i)]}")
            print(f"  - Is in jail?: {bool(state[3+(4*i)])}")

        # mortgageable
        i = 0
        n_players = len(self.players)
        start = 4*n_players

        for prop in self.properties:
            if prop.type in ["buildable", "railroad", "utility"]:
                print(prop.name)
                prop_info = state[start+(i*(n_players + 3)):start+(i*(n_players + 3)) + n_players + 3]
                for j in range(n_players):
                    print(f"  - Owned by player {j}: {bool(prop_info[j])}")
                #print(f"  - Owned by player {j}: {prop_info[j+2+(1*i)]}")
                print(f"  - Is mortgaged?: {bool(prop_info[n_players])}")
                print(f"  - Part of Monopoly?: {bool(prop_info[n_players+1])}")
                print(f"  - Frac of built houses: {(prop_info[n_players+2])}")
                i += 1

    def print_actionSpace(self, space):
        actions = []
        idxs = []
        elig_props = [x for x in self.properties if x.type in ["buildable", "railroad", "utility"]]
        buildable = [x for x in elig_props if x.type == "buildable"]
        if bool(space[0]):
            actions.append("End turn")
            idxs.append(0)
        elif bool(space[1]):
            actions.append("Bankrupt")
            idxs.append(1)
        mort = space[2:30]
        unmort = space[30:58]
        build = space[58:]
        morts = []
        unmorts = []
        builds = []
        for i in range(28):
            name = elig_props[i].name
            if bool(mort[i]):
                morts.append(("mortgage " + name, 2+i))
            if bool(unmort[i]):
                unmorts.append(("unmortgage " + name, 30+i))
            if i < 22 and bool(build[i]):
                builds.append(("build " + buildable[i].name, 58+i))

        return actions + [x[0] for x in morts] + [x[0] for x in unmorts] + [x[0] for x in builds], \
            idxs + [x[1] for x in morts] + [x[1] for x in unmorts] + [x[1] for x in builds]

    def getActionSpace(self, current_player):
        # 0: end turn available
        # 1: must declare bankrupt
        # can mortgage x28 [2:30]
        # 2x Brown
        # 4x Railroads
        # 2x util
        # 3x Light Blue
        # 3x magenta
        # 3x orange
        # 3x red
        # 3x yellow
        # 3x green
        # 2x blue
        # can unmortgage x28 [31:59]
        # can build x22 [60:92]
        # trade x28^2 == 784

        action_space = []
        mort = []
        unmort = []
        build = []

        player = self.players[current_player]
        nw, mortgageable, unmortgageable, buildable = player.calc_nw()

        action_space.append(1 * (player.money > 0))
        action_space.append(1 * ((player.money <= 0) and len(mortgageable) == 0))

        for prop in self.properties:
            if prop.type in ["buildable", "railroad", "utility"]:
                mort.append(1 * (prop in mortgageable))
                unmort.append(1 * (prop in unmortgageable))
                if prop.type == "buildable":
                    build.append(1 * (prop in buildable))
        action_space = action_space + mort + unmort + build
        #print(action_space[2:30] == mort)
        #print(action_space[30:58] == unmort)
        #print(action_space[58:80] == build)
        return action_space

    def step(self, action, winner_if_bankrupt = None):
        try:
            if len(action) == 1:
                action = action[0]
        except:
            print(action)
        player_in_step = self.current_player
        try:
            if sum(action) > 1 or sum(action) == 0:
                print(action)
                raise Exception("Invalid action")
        except:
            print(action)

        if bool(action[0]):
            # print("End turn")
            self.current_player += 1
            if self.current_player > len(self.players) - 1:
                self.current_player = 0
        elif bool(action[1]):
            # print("Bankrupt")
            self.players[player_in_step].bankrupt(winner_if_bankrupt)
        elif sum(action[2:30]) == 1:
            i = 0
            for prop in self.properties:
                if prop.type in ["buildable", "railroad", "utility"]:
                    if bool(action[2:30][i]):

                        worked = prop.mortgage()
                        #if worked is not None:
                            # print("mortgage on " + prop.name)
                        #else:
                            # print("could not mortgage")
                        break
                    i += 1
        elif sum(action[30:58]) == 1:
            i = 0
            for prop in self.properties:
                if prop.type in ["buildable", "railroad", "utility"]:
                    if bool(action[30:58][i]):
                        worked = prop.unmortgage()
                        #if worked:
                            #print("unmortgage on " + prop.name)
                        #else:
                            #print("cannot unmortgage")
                        break
                    i += 1
        elif sum(action[58:80]) == 1:
            i = 0
            for prop in self.properties:
                if prop.type in ["buildable"]:
                    if bool(action[58:80][i]):
                        worked = prop.build()
                        #if worked is not None:
                            #print("build on " + prop.name)
                        #else:
                            #print("Could not build")
                        break
                    i += 1
        p = len(self.players)
        c = self.c
        player = self.players[player_in_step]
        nw = player.calc_nw()[0] - player.money
        nws = [x.calc_nw()[0] - x.money for x in self.players if x != player]
        ms = [x.money for x in self.players]
        v = nw - sum(nws)

        num = (v/p)*c
        den = 1 + abs((v/p) * c)

        reward = num/den + (1/p)*(player.money/(1e-15 + sum(ms)))
        state = self.getCurrentState(player_in_step)
        done, winner = self.is_over()
        info = {"player": player.name, "winner": winner}
        return state, reward, done, info

    def env_roll(self, player):
        roll_finished = False
        num_doubles = 0
        winner_if_bankrupt = None
        while not roll_finished:
            r1 = random.randint(1, 6)
            r2 = random.randint(1, 6)

            roll_val = r1 + r2

            player.prev_roll = r1 + r2
            was_doubles = r1 == r2
            if was_doubles:
                num_doubles += 1

            if player.jailed:
                #print(f"Jailed (turn {player.jail_turns + 1})")
                #print(f"Roll: {r1}, {r2} ({roll_val})")
                if r1 == r2:
                    #print("Got out of jail!")
                    player.jailed = False
                    player.jail_turns = 0
                    player.current_location_ind = 10
                elif player.jail_turns > 2:
                    #print("Too many jail turns. Owe $50")
                    player.money -= 50
                    player.jailed = False
                    player.jail_turns = 0
                    player.current_location_ind = 10
                else:
                    player.jail_turns += 1
                roll_finished = True
            else:
                #print(f"{player.name}: Roll: {r1}, {r2} ({roll_val})")

                prev_loc = self.properties[player.current_location_ind]
                prev_ind = player.current_location_ind
                player.current_location_ind += roll_val

                if player.current_location_ind > 39:
                    player.current_location_ind = player.current_location_ind - 40
                    player.money += 200

                new_loc = self.properties[player.current_location_ind]
                new_ind = player.current_location_ind

                #print(f"{prev_loc.name} -> {new_loc.name} ({prev_ind} -> {new_ind})")


                winner_if_bankrupt = new_loc.landed_on(player, bot=True)
                # self.print_status(player)

                if r1 == r2:
                    if num_doubles == 2:
                        #print("Rolled 3 doubles in a row! Off to jail")
                        player.jailed = True
                        player.current_location_ind = 40
                        roll_finished = True
                else:
                    roll_finished = True
        return winner_if_bankrupt
    def game_loop(self):
        while running:
            over, winner = self.is_over()
            if over:
                print("Game is over!")
                print("Congrats " + winner.name)
                break

            input(f"Press any key to roll for player {self.players[self.current_player].name}")

            print("-------------------")
            print(self.getCurrentState(self.current_player))
            print(self.getActionSpace(self.current_player))
            self.roll(self.players[self.current_player])  # , forced_roll_1=7, forced_roll_2=5)

            self.current_player += 1
            if self.current_player > len(self.players) - 1:
                self.current_player = 0

    def is_over(self):
        winner = None
        for p in self.players:
            if not p.is_bankrupt and winner is None:
                winner = p
            elif not p.is_bankrupt and winner is not None:
                return False, None
        return True, winner

    def print_status(self, player):
        print(f"Money: {player.money}")
        print("Properties:")
        for prop_ind in player.properties:
            prop = self.properties[prop_ind]
            if prop.type == "buildable":
                print(
                    f"- {prop.name}. Is monopoly?: {prop.is_monopoly()}. Houses: {prop.houses}. Hotel: {prop.hotel}. Mortgaged: {prop.mortgaged}")
            else:
                print(f"- {prop.name}")

    def roll(self, player, num_doubles=0, forced_roll_1=None, forced_roll_2=None, forced_start=None, forced_end=None):
        r1 = random.randint(1, 6)
        r2 = random.randint(1, 6)

        if forced_roll_1 is not None:
            r1 = forced_roll_1
        if forced_roll_2 is not None:
            r2 = forced_roll_2

        roll_val = r1 + r2

        player.prev_roll = r1 + r2
        was_doubles = r1 == r2

        if player.jailed:
            print(f"Jailed (turn {player.jail_turns + 1})")
            print(f"Roll: {r1}, {r2} ({roll_val})")
            if r1 == r2:
                print("Got out of jail!")
                player.jailed = False
                player.jail_turns = 0
                self.roll(player, 0, r1, r2, forced_start=40)
            elif player.jail_turns > 2:
                print("Too many jail turns. Owe $50")
                player.money -= 50
                player.jailed = False
                player.jail_turns = 0
                self.roll(player, 0, r1, r2, forced_start=40)
            else:
                while True:
                    print("Press e to pass, p to pay $50 to get out, or j to use a jail card")
                    key = msvcrt.getch()

                    if key == b"e":
                        break
                    if key == b"p":
                        print("Paid to get out of jail")
                        player.money -= 50
                        player.jailed = False
                        player.jail_turns = 0
                        self.roll(player, 0, r1, r2, forced_start=40, forced_end=10)
                        break
                    if key == b"j":
                        if player.jail_cards > 0:
                            print("Used jail card")
                            player.jailed = False
                            player.jail_turns = 0
                            self.roll(player, 0, r1, r2, forced_start=40, forced_end=10)
                            break
                        else:
                            print("No jail cards!")

                player.jail_turns += 1
        else:
            winner_if_bankrupt = None
            came_from_jail = False
            if forced_start is not None:
                if forced_start == 40:
                    came_from_jail = True
                    player.current_location_ind = 10
                else:
                    player.current_location_ind = forced_start

            print(f"Roll: {r1}, {r2} ({roll_val})")

            starting_money = player.money
            prev_loc = self.properties[player.current_location_ind]
            prev_ind = player.current_location_ind
            player.current_location_ind += roll_val

            if forced_end is not None:
                player.current_location_ind = forced_end

            self.print_status(player)

            if player.current_location_ind > 39:
                player.current_location_ind = player.current_location_ind - 40
                print("Passed go (+200)")
                print("Balance: " + str(player.money))
                player.money += 200

            new_loc = self.properties[player.current_location_ind]
            new_ind = player.current_location_ind

            print(
                f"{prev_loc.name if not came_from_jail else 'Jail'} -> {new_loc.name} ({prev_ind if not came_from_jail else 'Jail'} -> {new_ind})")

            winner_if_bankrupt = new_loc.landed_on(player)
            if player.money != starting_money:
                self.print_status(player)

            # if player.can_buy():
            #    print(f"Can buy {new_loc.name}. Press y to buy. Press enter to continue.")
            #    key = msvcrt.getch()
            #    if key == b"y":
            #        print(f"Bought {new_loc.name}")
            #        player.buy()
            #        print_status(player, properties)

            if r1 == r2:
                if num_doubles == 2:
                    print("Rolled 3 doubles in a row! Off to jail")
                    player.jailed = True
                    player.current_location_ind = 40
                else:
                    self.roll(player, num_doubles + 1)

            turn_ended = False

            while not turn_ended and not was_doubles:
                print(
                    "Press b to buy houses/hotels, press m to mortgage, press u to unmortgage, press t to trade, press e to end turn")
                key = msvcrt.getch()
                if key == b"b":
                    i = 0
                    for prop_ind in player.properties:
                        prop = self.properties[prop_ind]
                        if prop.type == "buildable":
                            print(f"{i}: {prop.name}")
                            i += 1

                    inp = input("Type the index of the property to buy a house/hotel on")
                    try:
                        prop = self.properties[player.properties[int(inp)]]
                        resp = prop.build()
                        print(resp)
                        if resp is not None:
                            print(f"Built {resp} on " + prop.name)
                        else:
                            print("Unable to build on " + prop.name)
                    except:
                        print("Invalid input")

                if key == b"m":
                    i = 0
                    for prop_ind in player.properties:
                        prop = self.properties[prop_ind]
                        print(f"{i}: {prop.name}")
                        i += 1

                    inp = input("Type the index of the property to mortgage a house/hotel on (or whole property)")
                    try:
                        prop = self.properties[player.properties[int(inp)]]
                        resp = prop.mortgage()
                        if resp is not None:
                            print(f"Mortgaged {resp} on " + prop.name)
                        else:
                            print("Unable to mortgage " + prop.name)
                    except:
                        print("Invalid input")
                if key == b"u":
                    i = 0
                    for prop_ind in player.properties:
                        prop = self.properties[prop_ind]
                        print(f"{i}: {prop.name}")
                        i += 1

                    inp = input("Type the index of the property to unmortgage")
                    try:
                        prop = self.properties[player.properties[int(inp)]]
                        resp = prop.unmortgage()
                        if resp:
                            print(f"Unmortgaged " + prop.name)
                        else:
                            print("Unable to unmortgage " + prop.name)
                    except:
                        print("Invalid input")
                if key == b"e":
                    if player.money <= 0:
                        print(
                            "You must end durn with a balance greater than 0. Press b to declare bankruptcy. Press any key to go to mortgage")
                        key = msvcrt.getch()
                        if key == b"b":
                            player.bankrupt(winner_if_bankrupt)
                            break
                        else:
                            pass
                    else:
                        turn_ended = True
                        break
                if key == b"t":
                    pass
                self.print_status(player)


if __name__ == "__main__":
    g = game()
    g.game_loop()
