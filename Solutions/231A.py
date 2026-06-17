# Input

# the first input line contains a single iteger n  (1 <= n <= 1000) which is the number of problems in the contest.

# then n lines contain 3 integers each, each integer is a 0 or 1.

# if the first number in the line equals 1, then petya is sure about the problem's solution, or he isnt sure

# the second number shows vasya's view on the solution

# the third number shows tonya's view on the solution

# Output

# print a single intger - the number of problems the friends will implement on the contest. 

# Example input

#   3
#   1 1 0
#   1 1 1
#   1 0 0

# Example output

#   2

n = int(input())

count = 0

for i in range(n):
    p, v, t = map(int, input().split())

    if (p+v+t >= 2):
        count += 1

print(count)