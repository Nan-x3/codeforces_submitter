# 1 <= k <= n <= 50

# first line

# n k ## seperated by a space

# second line ocntains n space-seperated integers a1, a2, ...
# 0 <= a <= 100

# where a is the score earned by the participant who got the i-th place.

# non increasing sequence, that is, all i from 1 to (n - 1), ai >= ai + 1

# example input 

#   8 5
#   10 9 8 7 7 7 5 5 

# output 

#   6

n, k = map(int, input().split())

count = 0

scores = list(map(int, input().split()))
for score in scores:
    if score > 0 and score >= scores[k-1]:
        count += 1
    else:
        break

print(count)