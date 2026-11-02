# 死循环实验（阶段 3 · 第 3 课）
# 这个文件专门用来"看程序停不下来是什么样子"。
# 跑起来会疯狂刷屏，准备好按 Ctrl + C 打断。



count = 0
LIMIT = 5

while True:
    count = count + 1
    print("第",count,"次尝试")

    if count>=LIMIT:
        print("到",LIMIT,"次了，自己停下。")
        break