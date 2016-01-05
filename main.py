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
    """Car rental branch. It has a maximum capacity of cars (maxCapacity), cars which are available for hire (available)
and cars which need one day of service before they become available (queued).
"""
    def __init__(self, maxCapacity, available, queued):
        self.maxCapacity = maxCapacity
        self.available = available
        self.queued = queued

    def transferCars(self, carTransfers):
        """Transfer cars in and out. If carTransfer > 0, add cars, otherwise remove.
Raises exception if more cars are attempted removed than are available."""

        if carTransfers < 0:
            # When removing cars, make sure we don't go below 0 (if so raise exception)
            if self.available + carTransfers < 0:
                raise NotEnoughCarsException() 
            else:                
                self.available += carTransfers
        else:
            # When adding cars, cars exceeding the maximum capacity are thrown into a giant trash compactor
            freeSpots = self.maxCapacity - self.available - self.queued
            self.available += min(carTransfers, freeSpots)

    def __repr__(self):
        return "RentalBranch({0}, {1}, {2})".format(self.maxCapacity, self.available, self.queued)

    def __eq__(self, other):
        return self.maxCapacity == other.maxCapacity and self.available == other.available and self.queued == other.queued

    def __hash__(self):
        return hash((self.maxCapacity, self.available, self.queued))

class NotEnoughCarsException(BaseException):
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
            self.branchA.maxCapacity, self.branchA.available, self.branchA.queued, self.branchB.maxCapacity, self.branchB.available, self.branchB.queued)

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

    def __init__(self, maxCapacity):
        self.maxCapacity = maxCapacity # We model the policy as a sparse map so we need maxCapacity to know what the limits are
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
        self.valueMap = dict() # State instance to value

    def randomInitialization(self, maxCapacity):
        for totalA in range(maxCapacity+1):
            for qA in range(totalA+1):
                branchA = RentalBranch(maxCapacity, totalA-qA, qA)
                for totalB in range(maxCapacity+1):
                    for qB in range(totalB+1):
                        branchB = RentalBranch(maxCapacity, totalB-qB, qB)
                        self.valueMap[State(branchA, branchB)] = random.uniform(0,10)

    def __getitem__(self, key):
        return self.valueMap[key]

    def __setitem__(self, key, value):
        self.valueMap[key]=value


##    Finally, we need algorithms for evaluating the value of of states and actions
##    under given state value estimates and policies. In writing these algorithms
##    it is very handy to have iteraters over all possible states and actions.

def stateIter(maxCapacity):
    """Iterator over all possible states for two branches with specified maximum capacity"""
    for totalA in range(maxCapacity+1): 
        for queuedA in range(totalA+1):
            branchA = RentalBranch(maxCapacity, totalA-queuedA, queuedA)
            for totalB in range(maxCapacity+1):
                for queuedB in range(totalB+1):
                    branchB = RentalBranch(maxCapacity, totalB-queuedB, queuedB)
                    yield State(branchA, branchB)
                    
def actionIter(state):
    """Iterator over the transfers from A to B"""
    return range(-state.branchB.available, state.branchA.available+1)

def estimateStateValue(state, valueMap, policy):
    """Estimate the value of a state given the values of other states and a policy"""
    return estimateActionValue(state, policy[state], valueMap)

def estimateActionValue(state, action, valueMap):
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
    Income = - TRANSFER_COST * abs(action) # We always pay so it's always non-positive
    try:
        branchA.transferCars(-action)
        branchB.transferCars(action)
    except NotEnoughCarsException:
        return BAD_MOVE_COST

    # Construct probabilities for each rental scenario. Note that if customer count exceeds
    # the number of available cars, we turn away the extra customers.
    rentProbA = rentalProbabilities(branchA.available)
    rentProbB = rentalProbabilities(branchB.available)

    for (custA, probA) in enumerate(rentProbA):
        newBranchA = RentalBranch(branchA.maxCapacity, branchA.available - custA + branchA.queued, custA)
        for (custB, probB) in enumerate(rentProbB):
            newBranchB = RentalBranch(branchB.maxCapacity, branchB.available - custB + branchB.queued, custB)
            Income += probA*probB*( (custA+custB)*RENTAL_INCOME + DISCOUNT_RATE*valueMap[State(newBranchA, newBranchB)] )

    return Income

def rentalProbabilities(available):
    """List of probabilities for number of cars rented out. Index signifies number of cars, value is probability."""
    rentProb = [(RENT_RATE**n) / math.factorial(n) * math.exp(-RENT_RATE) for n in range(available)] # Poisson distribution
    rentProb.append(1-sum(rentProb)) # Customers equal or exceed available cars
    return rentProb

def printPolicy(policy):
    """ASCII representation of the policy.

Shows a matrix of the transfers to be made given the available cars in the two branches (A vertical, B horizontal).
The policy is shown for 0 queued cars.

Transfer values are shown as absolutes (to fit everything below 10 in a single cell).
"""
    printRows = []
    maxCapacity = policy.maxCapacity
    for availableA in range(maxCapacity, -1, -1):
        branchA = RentalBranch(maxCapacity, availableA, 0)
        states = [State(branchA, RentalBranch(maxCapacity, availableB, 0)) for availableB in range(0, maxCapacity+1)]
        transfers = [str(abs(policy[s])) for s in states]
        printRows.append(''.join(transfers))

    print('\n'.join(printRows))
        

def main(maxCapacity):
    valueChangeThreshold = 1
    policyChanged = True

    valueMap = ValueMap()
    valueMap.randomInitialization(maxCapacity)
    policy = Policy(maxCapacity)

    while policyChanged:
        # Update the value map to fit with the new policy
        print("*** Evaluating value map ***")
        maxValueChange = valueChangeThreshold+1
        while maxValueChange > valueChangeThreshold:
            maxValueChange = 0
            for state in stateIter(maxCapacity):
                oldValue = valueMap[state]
                newValue = estimateStateValue(state, valueMap, policy)
                valueMap[state] = newValue
                maxValueChange = max(maxValueChange, abs(newValue-oldValue))

        # Update the policy again
        print("*** Updating policy ***")
        policyChanged = False

        for state in stateIter(maxCapacity):
            actionVals = [(a, estimateActionValue(state, a, valueMap)) for a in actionIter(state)]
            best = max(actionVals, key=lambda e: e[1])
            if policy[state] != best[0]: # HORRORS if multiple best actions and we switch back and forth
                policyChanged=True
                policy[state]=best[0]
                oldState = state

    print('\n\n**********************\n\n')
    printPolicy(policy)
                
    
                
                
        
            
        
