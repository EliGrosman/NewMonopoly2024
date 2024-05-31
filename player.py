class player:
    def __init__(self, name, prop_ref):
        self.name = name
        self.money = 1000

        self.properties = []
        self.prop_ref = prop_ref
        self.jail_cards = 0
        self.jailed = False
        self.jail_turns = 0
        self.is_bankrupt = False

        self.current_location_ind = 0

    def calc_nw(self):
        nw = self.money
        mortgageable = []
        unmortgageable = []
        buildable = []

        for p in self.properties:
            prop = self.prop_ref[p]
            val = (prop.cost/2 if prop.mortgaged else prop.cost)
            if prop.mortgaged and self.money > (prop.cost/2):
                unmortgageable.append(prop)
            elif not prop.mortgaged:
                mortgageable.append(prop)

            if prop.type == "buildable":
                val += prop.build_cost * (prop.houses + 1*prop.hotel)

                if prop.is_monopoly() and (prop.houses < 4 or (prop.houses == 4 and not prop.hotel)) and (self.money >= prop.build_cost):
                    buildable.append(prop)
            nw += val
        return nw, mortgageable, unmortgageable, buildable
    def buy(self):
        prop = self.prop_ref[self.current_location_ind]
        if self.can_buy():
            self.properties.append(self.prop_ref.index(prop))
            prop.buy(self)

    def buy_ind(self, ind):
        prop = self.prop_ref[ind]
        if self.can_buy(ind):
            self.properties.append(self.prop_ref.index(prop))
            ret = prop.buy(self, ind)
        else:
            print("Cant buy!")

    def can_buy(self, ind=None):
        if ind is None:
            ind = self.current_location_ind
        prop = self.prop_ref[ind]
        if not prop.owned and prop.type and prop.type in ["buildable", "railroad", "utility"]:
            if self.money >= prop.cost:
                return True
        return False

    def bankrupt(self, winner):
        self.is_bankrupt = True
        if winner is not None:
            for prop_ind in self.properties:
                prop = self.prop_ref[prop_ind]
                prop.owner = winner
                winner.properties.append(prop_ind)
