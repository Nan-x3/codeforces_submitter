# 5 x 5 matrix. Contais twenty four 0s and one 1.

# Index is 1 - 5 from top to bottom and from left to right.

# In one move we can do only two transformations to the matrix:

# 1. swap two neightbouring matrix rows, that is rows with indices i and i+1 for some integer i where, 1 <= i <= 5
# 2. swap two neighbouring matrix columns, that is columns with indices j and j+1 for some integer j where, 1 <= j <= 5

# goal: we think the matrix looks beautiful if the single number one of the matrix is located in the middle.
# we need to minimise the number of moves needed to do this.

# example input

# 0 0 0 0 0
# 0 0 0 0 1
# 0 0 0 0 0
# 0 0 0 0 0
# 0 0 0 0 0

# output 

# 3

# This one's technically a path finding algorithm's simplest form isnt it? Let's go. I love this kinda stuff.

# Let's start with taking the input. we need to take a 5 x 5 matrix every time so lets do something along these lines.

for i in range(5):
    row = list(map(int, input().split()))

    # Now we need to determine where the one is in the matrix. 

    if 1 in row:
        row_index = i
        column_index = row.index(1)

# Now we use the indices to find the manhattan distance from the middle. This results in the minimum number of moves required.

print(abs(row_index - 2) + abs(column_index - 2))