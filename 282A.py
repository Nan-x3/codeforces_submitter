# only one variable called 'x' 

# only two operations
# ++ - increases the value of x by 1
# -- - decreases the value of x by 1

# a statement is a sequence consisting exactly one operation and one variable. the statement is written without spaces.

# executing a statement means applying an operation it contains

# initial value of x is 0

# goal is to find the final value

# Input

# The first line contains a single integer n where n = (1 <= n <= 150) - this is the number of statements in the programme.filter

# Next n lines contain a statement each.filter

# Example input

#   1
#   ++X

# Example output

#   1

x = 0

num = int(input())

for i in range(num):
    operator = input()

    if "++" in operator:
        x += 1
    elif "--" in operator:
        x -= 1

print(x)