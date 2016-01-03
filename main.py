import math
import random
import copy

MAX_CAPACITY = 20 # On second thought, don't use this
BAD_MOVE_COST = -1000
RENT_RATE = 5
DISCOUNT_RATE = 0.8

class RentalBranch:
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
    """A policy for transferring cars between rental branches."""

    # Possibly have max capacity as a member here, possibly throw exception in actionFromState

    def __init__(self, maxCapacity):
        self.maxCapacity = maxCapacity
        self.stateToActionMap = dict()

    def actionFromState(self, state):
        """Takes in a State instance and returns number of cars to transfer from branch A to B"""
        return self.stateToActionMap.get(state, 0)

    def __getitem__(self, key):
        return self.stateToActionMap.get(key, 0)

    def __setitem__(self, key, value):
        self.stateToActionMap[key]=value


class ValueMap:
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

    def value(self, state):
        return self.valueMap[state]

    def __getitem__(self, key):
        return self.valueMap[key]

    def __setitem__(self, key, value):
        self.valueMap[key]=value

class NotEnoughCarsException(BaseException):
    """Signifies insufficient cars in rental lot for intended operation."""    
    pass


def stateIter(maxCapacity):
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
    return estimateActionValue(state, policy[state], valueMap)

def estimateActionValue(state, action, valueMap):
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

##    print('Estimated value for ({0}, {1}): {2}'.format(state, action, value))
    return value
    

def printPolicy(policy):
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
##                if abs(newValue-oldValue) > maxValueChange:
##                    print('Big change for {0}: {1}'.format(state, newValue - oldValue))
                maxValueChange = max(maxValueChange, abs(newValue-oldValue))
##            print('Value change is {0}'.format(maxValueChange))

        # Update the policy again
        print("*** Updating policy ***")
        policyChanged = False

        oldState = None #Remove everything related to this

        for state in stateIter(maxCapacity):
##            print('Updating for state {0}'.format(state))
            actionVals = [(a, estimateActionValue(state, a, valueMap)) for a in actionIter(state)]
            best = max(actionVals, key=lambda e: e[1])
            if policy[state] != best[0]: # HORRORS if multiple best actions and we switch back and forth
                policyChanged=True
##                print('Changing policy for {0} from {1} to {2}'.format(state, policy[state], best[0]))
                policy[state]=best[0]
##                print('New policy for {0} is {1}'.format(state, policy[state]))
##                if oldState is not None:
##                    print('Policy for old {0} is {1}'.format(oldState, policy[oldState]))
                oldState = state
##
##        for k,v in policy.stateToActionMap.items():
##            if v != 0:
##                print("^^^ {0} ~ {1}".format(k,v))

    print('\n\n**********************\n\n')
    printPolicy(policy)
                
    
                
                
        
            
        
