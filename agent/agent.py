# 会自己多步干活的助手（阶段 3）
# 这个文件从零开始，一段一段加。
# 今天的目标：让它学会"自己判断要不要再查一次"。

import os
import requests
import datetime
import json


def get_today():
    return datetime.date.today().isoformat()

def count_words(text):
    return len(text)

def count_chars(text):
    return len(text.replace(" ", ""))

def ask(msgs):
    r = None
    try:
        r = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": "Bearer " + os.environ.get("DEEPSEEK_API_KEY", "")},
            json={"model": "deepseek-chat", "messages": msgs, "temperature": 0},
            proxies={"http": None, "https": None},
            timeout=30,
        )
        data = r.json()
    except Exception as e:
        print("   ⚠ 网络请求失败：", type(e).__name__, str(e)[:120])
        if r is not None:
            print("   ⚠ 状态码：", r.status_code, "| 响应前 200 字：", repr(r.text[:200]))
        return None

    if "error" in data:
        print("   ⚠ 接口返回错误：", data["error"].get("message", data["error"]))
        return None
    
    return data["choices"][0]["message"]["content"]

messages = [
    {"role":"system","content":"""你有两个工具可用：
     1.get_today()-查询今天的日期，不需要参数 
     2.count_words(text)-统计一段文字有多少个字,需要参数text
     3.count_chars(text)-统计文字有多少个字符（不含空格），需要参数text

     需要工具时,只输出一行JSON,不要解释:
     {"tool":"工具名","args":{"参数名":值}}
     不需要工具时，直接回答。

     【关于长期记忆】
    如果本次对话附带了"历史心情记录"，那是背景资料，用来回答用户关于心情的问题。
    不要对这份记录本身做字数统计或其他处理。
     
     【事实边界】
    1. 只回答你确实知道的内容；不确定就明确说"我不确定"。
    2. 不要编造书名、作者、数字、日期、链接这类具体信息。
    3. 需要实时数据但没有对应工具时，直接说明"我没有这个能力"，并告诉用户去哪里查。 """},
    
    {"role":"user","content":"这句话有多少个字：今天 心情 很好"},
]

last_call=""

if os.path.exists("mood.txt"):
    old = open("mood.txt", encoding="utf-8").read()
    messages[0]["content"] = messages[0]["content"] + "\n\n【历史心情记录】\n" + old
    print("[长期记忆] 载入历史心情：", len(old), "字")

KEEP=4

for step in range(1, 4):
    if len(messages)>KEEP+1:
        messages=messages[:1]+messages[-KEEP:]
        print("[裁剪] 太长了，只留 system + 最近", KEEP, "条")

    print("[记录本]", len(messages), "条")
    reply = ask(messages)
    if reply is None:
        print("⚠ 本轮调用失败，任务中止。")
        break
    print("[第", step, "轮] 模型：", reply)

    if reply.strip().startswith("{"):
        try:
            call = json.loads(reply)
        except Exception as e:
            print("   ⚠ JSON 解析失败：", e)
            print("   ⚠ 原始输出：", reply)
            break
            
        print("   → 它想用工具：", call["tool"])
        print("   → 参数是：", call["args"])

        signature=call["tool"]+str(call["args"])

        if signature==last_call:
            print("   ⚠ 检测到重复调用，强制停止。")
            break
        last_call=signature

        if call["tool"] == "get_today":
            result = get_today()
        elif call["tool"] == "count_chars":
            result = count_chars(call["args"]["text"])
        elif call["tool"] == "count_words":
            if "text" in call["args"]:
                result = count_words(call["args"]["text"])
            else:
                result="缺少参数 text"
        else:
            result="没有这个工具："+call["tool"]

        print("   → 工具返回：", result)
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content": "工具返回：" + str(result) + "，请回答。"})
    else:
        print("最终回答：", reply)
        break




