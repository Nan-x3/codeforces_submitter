# Rectangular board of M x N squares

# Unlimited standard 2 x 1 domino pieces.

# Allowed ti rotate the pieces. We are asked to place as many dominoes as possible ion the board so as to meet the following condiitons:

# 1. Each domino completely covers two squares.

# 2. No two dominoes overlap.

# 3. Each domino lies entirely inside the board. It is allowed to touch the edges of the board.

# Find the maximum number of dominoes, which can be placed under these restrictions.

# Input 

# the first input line contains two integers m and n

# 1  <= M <= N <= 16

# Output

# print the maximum number of dominoes, which can be placed on the board under these restrictions.

# Example Input:    2 4
# Example Output:   4

m, n = map(int, input().split())

print((m * n) // 2)