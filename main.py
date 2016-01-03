import math
import random
import copy

BAD_MOVE_COST = -1000 # The cost of an illegal 'move'.
RENT_RATE = 5 # Average number of customers per day
DISCOUNT_RATE = 0.8 # The future value of money (i.e., tomorrow's money is today worth DISCOUNT_RATE*(what it is worth tomorrow))

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
            if self.available + carTransfers < 0:
                raise NotEnoughCarsException()
            else:
                self.available += carTransfers
        else:
            freeSpots = self.maxCapacity - self.available - self.queued
            self.available += min(carTransfers, freeSpots)

    def __repr__(self):
        return "RentalBranch({0}, {1}, {2})".format(self.maxCapacity, self.available, self.queued)

    def __eq__(self, other):
        return self.maxCapacity == other.maxCapacity and self.available == other.available and self.queued == other.queued

    def __hash__(self):
        return hash((self.maxCapacity, self.available, self.queued))
                
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

class NotEnoughCarsException(BaseException):
    """Signifies insufficient cars in rental lot for intended operation."""    
    pass


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

    # Create copies of the branches as we will modify them with car transfers
    branchA = copy.copy(state.branchA)
    branchB = copy.copy(state.branchB)

    transferIncome = -2 * abs(action) # We always pay so it's always non-positive
    try:
        branchA.transferCars(-action)
        branchB.transferCars(action)
    except NotEnoughCarsException:
        return BAD_MOVE_COST

    rentProbA = [(RENT_RATE**n) / math.factorial(n) * math.exp(-RENT_RATE) for n in range(branchA.available)]
    rentProbA.append(1-sum(rentProbA)) # Customers equal or exceed available cars

    rentProbB = [(RENT_RATE**n) / math.factorial(n) * math.exp(-RENT_RATE) for n in range(branchB.available)]
    rentProbB.append(1-sum(rentProbB)) # Customers equal or exceed available cars

    value = transferIncome
    for (custA, probA) in enumerate(rentProbA):
        newBranchA = RentalBranch(branchA.maxCapacity, branchA.available - custA + branchA.queued, custA)
        for (custB, probB) in enumerate(rentProbB):
            newBranchB = RentalBranch(branchB.maxCapacity, branchB.available - custB + branchB.queued, custB)
            value += probA*probB*( (custA+custB)*10 + DISCOUNT_RATE*valueMap[State(newBranchA, newBranchB)] )

    return value
    

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
                
    
                
                
        
            
        
