import math
import random
import copy

BAD_MOVE_COST = -1000 # The cost of an illegal 'move'.
RENT_RATE     = 5     # Average number of customers per day
DISCOUNT_RATE = 0.9   # The future value of money (i.e., tomorrow's money is today worth DISCOUNT_RATE*(what it is worth tomorrow))
RENTAL_INCOME = 10
TRANSFER_COST = 2


##    We start by setting up the world. A state of the world is characterized by the
##    states of the two car rental branches.
##
##    A state of a single rental branch is characterized by (1) the total car capacity
##    of the branch, (2) how many cars are ready for rental, and (3) how many cars are
##    currently being serviced and will be ready for rental the next day.

class RentalBranch:
    """Car rental branch. It has a maximum capacity of cars (max_capacity), cars which are available for hire (available)
    and cars which need one day of service before they become available (queued).
    """
    def __init__(self, max_capacity, available, queued):
        self.max_capacity = max_capacity
        self.available = available
        self.queued = queued

    def transfer_cars(self, car_transfers):
        """Transfer cars in and out. If carTransfer > 0, add cars, otherwise remove.
        Raises exception if more cars are attempted removed than are available.
        """

        if car_transfers < 0:
            # When removing cars, make sure we don't go below 0 (if so raise exception)
            if self.available + car_transfers < 0:
                raise NotEnoughCarsException() 
            else:                
                self.available += car_transfers
        else:
            # When adding cars, cars exceeding the maximum capacity are thrown into a giant trash compactor
            free_spots = self.max_capacity - self.available - self.queued
            self.available += min(car_transfers, free_spots)

    def __repr__(self):
        return "RentalBranch({0}, {1}, {2})".format(self.max_capacity, self.available, self.queued)

    def __eq__(self, other):
        return self.max_capacity == other.max_capacity and self.available == other.available and self.queued == other.queued

    def __hash__(self):
        return hash((self.max_capacity, self.available, self.queued))

class Error(Exception):
    """Base exception for the script"""
    pass

class NotEnoughCarsException(Error):
    """Signifies insufficient cars in rental lot for intended operation."""    
    pass

##    The state of the world consists of the states of rental branch A and B
                
class State:
    """A state of the game. Determined by two rental branches, branchA and branchB."""
    def __init__(self, branchA, branchB):
        self.branchA = branchA
        self.branchB = branchB

    def __repr__(self):
        return "State(({0},{1},{2}), ({3},{4},{5}))".format(
            self.branchA.max_capacity, self.branchA.available, self.branchA.queued, self.branchB.max_capacity, self.branchB.available, self.branchB.queued)

    def __eq__(self, other):
        return self.branchA == other.branchA and self.branchB == other.branchB

    def __hash__(self):
        return hash((self.branchA, self.branchB))


##    Our ultimate aim is to construct an optimal policy for transfers between the
##    branches A and B. A policy maps a state of the world to the signed number of
##    cars to be transferred from A to B.

class Policy:
    """A policy for transferring cars between rental branches.

    Essentially a dictionary which maps states to an amount of cars to transfer from branch A to B. Negative numbers
    signify a net transfer from B to A.
    """

    def __init__(self, max_capacity):
        self.max_capacity = max_capacity # We model the policy as a sparse map so we need max_capacity to know what the limits are
        self.stateToActionMap = dict()

    def __getitem__(self, key):
        return self.stateToActionMap.get(key, 0)

    def __setitem__(self, key, value):
        self.stateToActionMap[key]=value

##    To construct a policy we need to have an estimate of the value of each state of the
##    world under the mythical optimal policy. I.e., a dictionary with keys being states
##    and the values being dollar value estimates. The ValueMap stores this information
##    for us.

class ValueMap:
    """Map (dictionary) of state to estimated dollar value"""
    
    def __init__(self):
        self.value_map = dict() # State instance to value

    def random_initialization(self, max_capacity):
        for totalA in range(max_capacity+1):
            for qA in range(totalA+1):
                branchA = RentalBranch(max_capacity, totalA-qA, qA)
                for totalB in range(max_capacity+1):
                    for qB in range(totalB+1):
                        branchB = RentalBranch(max_capacity, totalB-qB, qB)
                        self.value_map[State(branchA, branchB)] = random.uniform(0, 10)

    def __getitem__(self, key):
        return self.value_map[key]

    def __setitem__(self, key, value):
        self.value_map[key]=value


##    Finally, we need algorithms for evaluating the value of of states and actions
##    under given state value estimates and policies. In writing these algorithms
##    it is very handy to have iteraters over all possible states and actions.

def state_iter(max_capacity):
    """Iterator over all possible states for two branches with specified maximum capacity"""
    for totalA in range(max_capacity+1): 
        for queuedA in range(totalA+1):
            branchA = RentalBranch(max_capacity, totalA-queuedA, queuedA)
            for totalB in range(max_capacity+1):
                for queuedB in range(totalB+1):
                    branchB = RentalBranch(max_capacity, totalB-queuedB, queuedB)
                    yield State(branchA, branchB)
                    
def action_iter(state):
    """Iterator over the transfers from A to B"""
    return range(-state.branchB.available, state.branchA.available+1)

def estimate_state_value(state, value_map, policy):
    """Estimate the value of a state given the values of other states and a policy"""
    return estimate_action_value(state, policy[state], value_map)

def estimate_action_value(state, action, value_map):
    """Estimate the value of a state/action pair given the values of the other states"""

    ##    The estimated value of a (state, action) pair is found as follows:
    ##    1. Transfers cars according to the action and record the transfer cost
    ##    2. Construct the possible rental scenarios (a Poisson distribution of customers for each branch)
    ##    3. For each scenario, (a) record rental income, (b) move rented cars to queued and queued to available,
    ##        (c) record discounted future income from the new state according to the value map
    ##    4. Estimated value is transfer cost + probability-weighted sum of rental income and new state value
    ##        for each scenario in 3.

    # Create copies of the branches as we will modify them with car transfers
    branchA = copy.copy(state.branchA)
    branchB = copy.copy(state.branchB)

    # Transfer cars and record transfer costs
    income = - TRANSFER_COST * abs(action) # We always pay so it's always non-positive
    try:
        branchA.transfer_cars(-action)
        branchB.transfer_cars(action)
    except NotEnoughCarsException:
        return BAD_MOVE_COST

    # Construct probabilities for each rental scenario. Note that if customer count exceeds
    # the number of available cars, we turn away the extra customers.
    rent_probA = rental_probabilities(branchA.available)
    rent_probB = rental_probabilities(branchB.available)

    for (custA, probA) in enumerate(rent_probA):
        newBranchA = RentalBranch(branchA.max_capacity, branchA.available - custA + branchA.queued, custA)
        for (custB, probB) in enumerate(rent_probB):
            newBranchB = RentalBranch(branchB.max_capacity, branchB.available - custB + branchB.queued, custB)
            income += probA*probB*( (custA+custB)*RENTAL_INCOME + DISCOUNT_RATE*value_map[State(newBranchA, newBranchB)] )

    return income

def rental_probabilities(available):
    """List of probabilities for number of cars rented out. Index signifies number of cars, value is probability."""
    rent_prob = [(RENT_RATE**n) / math.factorial(n) * math.exp(-RENT_RATE) for n in range(available)] # Poisson distribution
    rent_prob.append(1-sum(rent_prob)) # Customers equal or exceed available cars
    return rent_prob

def print_policy(policy):
    """ASCII representation of the policy.

    Shows a matrix of the transfers to be made given the available cars in the two branches (A vertical, B horizontal).
    The policy is shown for 0 queued cars.

    Transfer values are shown as absolutes (to fit everything below 10 in a single cell).
    """
    print_rows = []
    max_capacity = policy.max_capacity
    for availableA in range(max_capacity, -1, -1):
        branchA = RentalBranch(max_capacity, availableA, 0)
        states = [State(branchA, RentalBranch(max_capacity, availableB, 0)) for availableB in range(0, max_capacity+1)]
        transfers = [str(abs(policy[s])) for s in states]
        print_rows.append(''.join(transfers))

    print('\n'.join(print_rows))
        

def main(max_capacity):
    value_change_threshold = 1
    policy_changed = True

    value_map = ValueMap()
    value_map.random_initialization(max_capacity)
    policy = Policy(max_capacity)

    while policy_changed:
        # Update the value map to fit with the new policy
        print("*** Evaluating value map ***")
        max_value_change = value_change_threshold+1
        while max_value_change > value_change_threshold:
            max_value_change = 0
            for state in state_iter(max_capacity):
                old_value = value_map[state]
                new_value = estimate_state_value(state, value_map, policy)
                value_map[state] = new_value
                max_value_change = max(max_value_change, abs(new_value-old_value))

        # Update the policy again
        print("*** Updating policy ***")
        policy_changed = False

        for state in state_iter(max_capacity):
            actionVals = [(a, estimate_action_value(state, a, value_map)) for a in action_iter(state)]
            best = max(actionVals, key=lambda e: e[1])
            if policy[state] != best[0]: # HORRORS if multiple best actions and we switch back and forth
                policy_changed=True
                policy[state]=best[0]
                old_state = state

    print('\n\n**********************\n\n')
    print_policy(policy)
                
    
                
                
        
            
        
