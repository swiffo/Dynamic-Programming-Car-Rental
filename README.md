# Dynamic-Programming-Car-Rental
Simple reinforcement learning problem solved with dynamic programming.

The problem is taken from the book *Reinforcement Learning* by Richard S. Sutton and Andrew G. Barto and is as follows:

> Jack manages two branches of a car rental company. Each day a Poisson-distributed number of customers come to each location and for each car rented out, Jack earns $10. Any car rented is returned at the end of the day but must spend the next day being serviced (not available for renting). Both rentable and serviced cars take up space and each branch has an upper limit to the cars that can be stored. Jack is able to transfer cars between the branches at the cost of $2 per car overnight. Only cars not being serviced can be transferred and transferred cars are available for rent at the new branch the next day.

> **What is the optimal transfer policy of cars between branches?**

Solution
========

Below is a solution map for two branches with a capacity of 20, daily customers being Poisson-distributed with a mean of 5, rental income being $10/car, transfer cost being 2$/car and the discount rate for future money being 0.9/day.

What is shown is the unsigned number of cars to be transferred between the two rental branches with the x- and y-axes signifying the number of available cars in each branch (0-20) with zero cars being serviced.
```
876654321100000000000
776554321000000000000
766544321000000000000
765543321000000000000
665443221000000000000
655433211000000000000
654432210000000000000
554332110000000000000
544322100000000000000
443321100000000000000
433221000000000000000
432211000000000000001
332110000000000111111
322100000000011122222
221100000001112223333
211000000111222333444
110000001122233344455
100000111223334445556
000001122233444555666
000011223334455566677
000112233444556667778
```
