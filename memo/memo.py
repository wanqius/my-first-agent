import os
import requests

print("你好，我是心情小助手。")

mood = input("今天心情怎么样？随便说说：")

# 新增 1：先检查有没有输入
if mood.strip() == "":
    print("你还没说话呢，下次再来。")
    exit()

# 新增 2：先检查 Key 有没有设
key = os.environ.get("DEEPSEEK_API_KEY", "")
if key == "":
    print("没找到 API Key。请先在命令行设置：set DEEPSEEK_API_KEY=sk-你的key")
    exit()

with open("mood.txt", "a", encoding="utf-8") as f:
    f.write(mood + "\n")

with open("mood.txt", "r", encoding="utf-8") as f:
    history = f.read()

# 新增 3：用 try 包住发请求那段
try:
    response = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": "Bearer " + key},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "我最近的心情记录：\n" + history + "\n请用一句话回应我，不超过25字。"}],
        },
        timeout=30,
    )
    data = response.json()

    if "error" in data:
        print("模型说：", data["error"]["message"])
    else:
        print(data["choices"][0]["message"]["content"])

except Exception as e:
    print("出问题了：", type(e).__name__, e)
