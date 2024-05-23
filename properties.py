from reference import PROPS_REF
import random
import msvcrt


class property_base:
    def __init__(self, name):
        self.name = name.strip()
        self.buyable = False
        self.owned = False
        self.type = None

    def landed_on(self, player, bot=False):
        pass


class tojail(property_base):
    def __init__(self):
        super().__init__("Go to Jail")
        self.type = "tojail"

    def landed_on(self, player, bot=False):
        # print("Sent to jail!")
        player.jailed = True
        player.current_location_ind = 40


class add_money(property_base):
    def __init__(self, name, value):
        super().__init__(name)
        self.value = value

    def landed_on(self, player, bot=False):
        player.money += self.value


class ownable(property_base):
    def __init__(self, name, cost, rent):
        super().__init__(name)
        self.buyable = True
        self.cost = cost
        self.rent = rent

        self.owned = False
        self.owner = None

        self.mortgaged = False

    def landed_on(self, player, bot=False):
        self.prompt_buy(player, bot)

        if self.owned and not self.mortgaged and self.owner is not player:
            # print(f"Owes {self.calc_rent()} to {self.owner.name}")
            player.money -= self.calc_rent()
            self.owner.money += self.calc_rent()
            return self.owner
        return None

    def calc_rent(self):
        return 0

    def prompt_buy(self, player, bot):
        if player.can_buy():
            # print(f"Can buy {self.name}. Press y to buy. Press enter to continue.")
            if bot and player.money >= self.cost*1.2:
                # print(f"Bought {self.name}")
                player.buy()
            elif not bot:
                key = msvcrt.getch()
                if key == b"y":
                    print(f"Bought {self.name}")
                    player.buy()
    def mortgage(self):
        if not self.mortgaged:
            self.mortgaged = True
            self.owner.money += self.cost / 2
            return True
        return None

    def unmortgage(self):
        if self.mortgaged:
            self.mortgaged = False
            self.owner.money -= self.cost / 2
            return True
        return False

    def buy(self, player, ind = None):
        if not self.owned:
            player.money -= self.cost
            self.owner = player
            self.owned = True
            return True
        return False


class buildable(ownable):
    def __init__(self, name, cost, rent, build_cost):
        super().__init__(name, cost, rent)
        self.type = "buildable"
        self.build_cost = build_cost
        self.houses = 0
        self.hotel = False
        self.set = None
        self.owner = None

    def calc_rent(self):
        offset = self.houses + (1 if self.hotel else 0)
        if offset == 0 and self.is_monopoly():
            return self.rent[0]*2
        return self.rent[0 + offset]

    def pass_set(self, set):
        self.set = set

    def is_monopoly(self):
        for prop in self.set:
            if prop.owner is None or prop.owner is not self.owner:
                return False
        return True

    def build(self):
        if self.owner is not None and self.is_monopoly() and not self.mortgaged:
            if self.owner.money >= self.build_cost:
                if self.hotel:
                    return None
                if self.houses == 4:
                    self.hotel = True
                    self.owner.money -= self.build_cost
                    return "Hotel"
                else:
                    self.houses += 1
                    self.owner.money -= self.build_cost
                    return "House"
        return None
    def mortgage(self):
        if self.owner is not None:
            if self.houses > 0:
                if self.hotel:
                    self.hotel = False
                    self.owner.money += self.build_cost
                    return "Hotel"
                else:
                    self.houses -= 1
                    self.owner.money += self.build_cost
                    return "House"
            else:
                return super().mortgage()



class railroad(ownable):
    def __init__(self, name, cost, rent):
        super().__init__(name, cost, rent)
        self.rails = None
        self.buyable = True
        self.type = "railroad"

    def is_monopoly(self):
        return self.get_owned() == 4
    def get_owned(self):
        num = 0
        if self.owner is None:
            return 0

        for rail in self.rails:
            if rail.owner == self.owner:
                num += 1
        return num

    def pass_rails(self, rails):
        self.rails = rails

    def calc_rent(self):
        return self.rent[self.get_owned() - 1]


class utility(ownable):
    def __init__(self, name, cost):
        super().__init__(name, cost, [])
        self.buyable = True
        self.type = "utility"
        self.utils = None
        self.cost = cost

    def is_monopoly(self):
        return self.get_owned() == 2
    def landed_on(self, player, bot=False):
        roll = player.prev_roll
        self.prompt_buy(player, bot)
        if self.owned and self.owner is not player:
            rent = 0
            if self.get_owned() == 1:
                # print(f"Owes 4xRoll (4*{roll} = {4 * roll}) to {self.owner.name}")
                rent = 4 * roll
            elif self.get_owned() == 2:
                # print(f"Owes 10xRoll (10*{roll} = {10 * roll}) to {self.owner.name}")
                rent = 10 * roll

            player.money -= rent
            self.owner.money += rent

    def get_owned(self):
        num = 0
        if self.owner is None:
            return 0

        for util in self.utils:
            if util.owner == self.owner:
                num += 1
        return num

    def pass_util(self, util):
        self.utils = util


class chance_chest(property_base):
    def __init__(self, name, deck, game):
        super().__init__(name)
        self.deck = deck
        self.game = game
        self.used = []
        self.properties = []

    def landed_on(self, player, bot):
        if len(self.deck) == 0:
            self.deck = self.used.copy()
            random.shuffle(self.deck)
            self.used = []

        card = self.deck[0]
        self.deck = self.deck[1:]
        self.used.append(card)

        # print(card["text"])

        match card["type"]:
            case "move":
                if card["value"] == "jail":
                    player.current_location_ind = 40
                    player.jailed = True
                else:
                    while True:
                        player.current_location_ind += 1
                        if player.current_location_ind > 39:
                            player.current_location_ind = player.current_location_ind - 40
                        if player.current_location_ind == 0:
                            # print("Passed go (+200)")
                            player.money += 200

                        comp_val = player.current_location_ind
                        # print(f"{card['value']}: {comp_val}")
                        if card["value"] == "railroad" or card["value"] == "utility":
                            comp_val = self.properties[player.current_location_ind].type


                        if comp_val == card["value"]:
                            prop = self.properties[player.current_location_ind]
                            if card["value"] != 0:
                                prop.landed_on(player, bot)
                            break
            case "add_money":
                player.money += card["value"]
            case "jailcard":
                player.jail_cards += 1
            case "repairs":
                houses = 0
                hotels = 0
                for prop_ind in player.properties:
                    prop = self.properties[prop_ind]
                    if prop.type == "buildable":
                        hotels += 1 if prop.hotel else 0
                        houses += prop.houses if not prop.hotel else 0
                val = (houses * card["house"]) + (hotels + card["hotel"])
                # print("Pay " + str(val))
                player.money -= val
            case "add_money_all":
                total = 0
                for p in self.game.players:
                    if player is not player:
                        p.money += card["value"]
                        total += card["value"]
                        player.money -= card["value"]
                # print("Total owed: " + str(total))
            case "go_back":
                player.current_location_ind -= card["value"]
                prop = self.properties[player.current_location_ind]
                # print("Chance -> " + prop.name)
                prop.landed_on(player, bot)
            case _:
                print("Unknown card type " + card["type"])


def init_properties(chance_deck, community_deck, game):
    properties = []
    rails = []
    utils = []
    community = chance_chest("Community Chest", community_deck, game)
    chance = chance_chest("Chance", chance_deck, game)

    for prop in PROPS_REF["properties"]:
        if prop["type"] == "add_money":
            properties.append(add_money(prop["name"], prop["value"]))
        elif prop["type"] == "buildable":
            properties.append(buildable(prop["name"], prop["cost"], prop["rent"], prop["build_cost"]))
        elif prop["type"] == "chance_chest":
            if prop["name"].strip() == "Community Chest":
                properties.append(community)
            if prop["name"].strip() == "Chance":
                properties.append(chance)
        elif prop["type"] == "railroad":
            rail = railroad(prop["name"], prop["cost"], prop["rent"])
            rails.append(rail)
            properties.append(rail)
        elif prop["type"] == "utility":
            util = utility(prop["name"], prop["cost"])
            utils.append(util)
            properties.append(util)
        elif prop["type"] == "none":
            properties.append(property_base(prop["name"]))
        elif prop["type"] == "tojail":
            properties.append(tojail())

    for i in range(len(properties)):
        prop = properties[i]
        if prop.type == "buildable":
            s = [properties[j] for j in PROPS_REF["properties"][i]["set"]]
            prop.pass_set(s)
        if prop.type == "railroad":
            prop.pass_rails(rails)
        if prop.type == "utility":
            prop.pass_util(utils)

    community.properties = chance.properties = properties

    return properties
