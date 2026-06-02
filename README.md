# 基于火山引擎 RTC 与 RAG 的实时语音智能客服系统

这是一个面向课程咨询场景的实时语音智能客服项目，基于开源 Demo `ark_aigc_demo` 二次开发。项目完成了从用户语音输入、RTC 实时传输、ASR 识别、CustomLLM 回调、自定义 RAG 检索、豆包大模型生成，到 TTS 语音播报的完整闭环。

项目目标是把一个官方 AIGC Demo 改造成可用于实习简历展示的工程项目：不仅能跑通实时语音对话，还能讲清楚 RAG、RTC、ASR/TTS、回调调试和服务端工程化。

## 项目亮点

- 使用 React + 火山 RTC SDK 实现实时语音通话和字幕展示。
- 使用 FastAPI 搭建自定义 AI 后端，接收火山 `CustomLLM` 回调。
- 接入火山知识库，实现课程咨询场景下的 RAG 检索增强。
- 使用 OpenAI Chat Completions 兼容 SSE 响应，让 RTC 云端可以流式消费 LLM 输出。
- 通过 NATAPP 将本地 RAG 服务映射到公网，解决云端回调本地服务的调试问题。
- 支持 `/debug/rag`、`/debug/chat`、`/health` 等调试接口，方便面试演示和链路排障。

## 核心链路

```text
用户浏览器
  -> React 前端
  -> 火山 RTC 房间
  -> 云端 ASR 语音识别
  -> CustomLLM 回调公网 URL
  -> FastAPI RAG 后端
  -> 火山知识库检索
  -> 豆包/方舟大模型流式生成
  -> 云端 TTS 语音合成
  -> RTC 远端音频流播放
```

## 目录说明

```text
ark_aigc_demo/
├─ src/                 # React 前端，负责进房、麦克风、字幕、通话 UI
├─ Server/              # Node 版官方基础后端，适合 ArkV3 原始 Demo
├─ server_python/       # Python 版基础后端示例
└─ rag_llm_server/      # Python FastAPI RAG 后端，本项目接入 CustomLLM 的重点
```

## RAG 后端环境变量

复制示例文件并填写真实配置：

```powershell
cd C:\Users\Fergeson\Desktop\AI智能语音客服\ark_aigc_demo\rag_llm_server
Copy-Item .env.example .env
```

需要填写的字段见：

```text
rag_llm_server/.env.example
```

注意：

- `.env` 存放真实 AK、SK、Token、API Key，不要提交到 GitHub。
- `SERVER_URL` 只填写公网基础地址，例如 `http://xxx.natappfree.cc`，不要加 `/api/chat_callback`。
- 使用 NATAPP 免费 HTTP 隧道时，代码会在 `LLMConfig` 中携带 `Feature: "{\"Http\":true}"`。

## 启动步骤

需要同时保持三个窗口运行。

### 1. 启动 RAG 后端

```powershell
cd C:\Users\Fergeson\Desktop\AI智能语音客服\ark_aigc_demo\rag_llm_server
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 3001
```

### 2. 启动 NATAPP

```powershell
cd C:\Users\Fergeson\Downloads
.\natapp.exe -authtoken=你的隧道token
```

确认 NATAPP 显示：

```text
Forwarding http://xxx.natappfree.cc -> http://127.0.0.1:3001
```

然后将 `.env` 中的 `SERVER_URL` 改成这个公网地址，并重启 RAG 后端。

### 3. 启动前端

```powershell
cd C:\Users\Fergeson\Desktop\AI智能语音客服\ark_aigc_demo
npm run dev
```

浏览器打开：

```text
http://localhost:3000
```

## 调试接口

### 健康检查

```text
GET http://localhost:3001/health
```

用于检查 AK/SK、Ark、RTC、ASR、TTS、知识库和公网回调地址是否配置齐全。

### 知识库检索

```text
GET http://localhost:3001/debug/rag?query=课程要学多久
```

用于确认火山知识库检索是否正常。

### 文本问答调试

```text
POST http://localhost:3001/debug/chat
```

请求体示例：

```json
{
  "history": [],
  "question": "课程要学多久？"
}
```

### CustomLLM 回调接口

```text
POST http://localhost:3001/api/chat_callback
```

火山 RTC 云端会请求该接口。接口返回 `text/event-stream`，并以 `data: [DONE]` 结束。

## 面试讲法

可以用下面这段概括项目：

```text
我基于火山引擎 RTC 和豆包大模型实现了一个实时语音智能客服系统。前端通过 RTC SDK 采集并发布用户语音，云端 Agent 完成 ASR 识别后，通过 CustomLLM 回调我的 FastAPI RAG 后端。后端检索火山知识库，把检索结果合并进系统提示词，再调用豆包模型流式生成回答，最后由云端 TTS 合成为语音并通过 RTC 播放给用户。
```

重点可以展开：

- 为什么使用 RTC：低延迟、弱网优化、音频 3A、支持打断。
- RAG 如何接入：`CustomLLM.Url` 回调到 FastAPI，后端检索知识库后调用 LLM。
- 如何调试：`/health` 看配置，`/debug/rag` 看检索，NATAPP 暴露公网回调。
- 遇到的问题：HTTP 回调需要 `Feature: "{\"Http\":true}"`，NATAPP 地址失效会导致云端无法回调。

---

# 交互式AIGC场景 AIGC Demo

此 Demo 为简化版本, 如您有 1.5.x 版本 UI 的诉求, 可切换至 1.5.1 分支。
跑通阶段时, 无须关心代码实现，仅需按需完成 `Server/scenes/*.json` 的场景信息填充即可。

## 简介
- 在 AIGC 对话场景下，火山引擎 AIGC-RTC Server 云端服务，通过整合 RTC 音视频流处理，ASR 语音识别，大模型接口调用集成，以及 TTS 语音生成等能力，提供基于流式语音的端到端AIGC能力链路。
- 用户只需调用基于标准的 OpenAPI 接口即可配置所需的 ASR、LLM、TTS 类型和参数。火山引擎云端计算服务负责边缘用户接入、云端资源调度、音视频流压缩、文本与语音转换处理以及数据订阅传输等环节。简化开发流程，让开发者更专注在对大模型核心能力的训练及调试，从而快速推进AIGC产品应用创新。     
- 同时火山引擎 RTC拥有成熟的音频 3A 处理、视频处理等技术以及大规模音视频聊天能力，可支持 AIGC 产品更便捷的支持多模态交互、多人互动等场景能力，保持交互的自然性和高效性。 

## 【必看】环境准备
**Node 版本: 16.0+**

### 1. 运行环境
需要准备两个 Terminal，分别启动服务端和前端页面。

### 2. 服务开通
开通 ASR、TTS、LLM、RTC 等服务，可参考 [开通服务](https://www.volcengine.com/docs/6348/1315561?s=g) 进行相关服务的授权与开通。

### 3. 场景配置
`Server/scenes/*.json`

您可以自定义具体场景, 并按需根据模版填充 `SceneConfig`、`AccountConfig`、`RTCConfig`、`VoiceChat` 中需要的参数。

Demo 中以 `Custom` 场景为例，您可以自行新增场景。

注意：
- `SceneConfig`：场景的信息，例如名称、头像等。
- `AccountConfig`：场景下的账号信息，https://console.volcengine.com/iam/keymanage/ 获取 AK/SK。
- `RTCConfig`：场景下的 RTC 配置。
    - AppId、AppKey 可从 https://console.volcengine.com/rtc/aigc/listRTC 中获取。
    - RoomId、UserId 可自定义也可不填，交由服务端生成。
- `VoiceChat`: 场景下的 AIGC 配置。
    - 可参考 https://www.volcengine.com/docs/6348/1558163 中参数描述，完整填写参数内容。
    - 可通过 [快速跑通 Demo](https://console.volcengine.com/rtc/aigc/run?s=g) 快速获取参数, 跑通后点击右上角 `接入 API` 按钮复制相关代码贴到 JSON 配置文件中即可。
## 快速开始
请注意，服务端和 Web 端都需要启动, 启动步骤如下:
### 服务端
进到项目根目录
#### 安装依赖
```shell
cd Server
yarn
```
#### 运行项目
```shell
yarn dev
```

### 前端页面
进到项目根目录
#### 安装依赖
```shell
yarn
```
#### 运行项目
```shell
yarn dev
```

### 常见问题
| 问题 | 解决方案 |
| :-- | :-- |
| 如何使用第三方模型、Coze Bot | 模型相关配置代码对应目录 `src/config/scenes/` 下json 文件，填写对应官方模型/ Coze/ 第三方模型的参数后，可点击页面上的 "修改 AI 人设" 进行切换。 |
| **启动智能体之后, 对话无反馈，或者一直停留在 "AI 准备中, 请稍侯"；在启用数字人的情况下，一直停留在“数字人准备中，请稍候”** | <li>可能因为控制台中相关权限没有正常授予，请参考[流程](https://www.volcengine.com/docs/6348/1315561?s=g)再次确认下是否完成相关操作。此问题的可能性较大，建议仔细对照是否已经将相应的权限开通。</li><li>参数传递可能有问题, 例如参数大小写、类型等问题，请再次确认下这类型问题是否存在。</li><li>相关资源可能未开通或者用量不足/欠费，请再次确认。</li><li>**请检查当前使用的模型 ID / 数字人 AppId / Token 等内容都是正确且可用的。**</li><li>数字人服务有并发限制，当达到并发限制时，同样会表现为一直停留在“数字人准备中”状态</li> |
| **浏览器报了 `Uncaught (in promise) r: token_error` 错误** | 请检查您填在项目中的 RTC Token 是否合法，检测用于生成 Token 的 UserId、RoomId 以及 Token 本身是否与项目中填写的一致；或者 Token 可能过期, 可尝试重新生成下。 |
| **[StartVoiceChat]Failed(Reason: The task has been started. Please do not call the startup task interface repeatedly.)** 报错 | 如果设置的 RoomId、UserId 为固定值，重复调用 startAgent 会导致出错，只需先调用 stopAgent 后再重新 startAgent 即可。 |
| 为什么麦克风、摄像头开启失败？浏览器报了`TypeError: Cannot read properties of undefined (reading 'getUserMedia')` | 检查当前页面是否为[安全上下文](https://developer.mozilla.org/zh-CN/docs/Web/Security/Secure_Contexts)（简单来说，检查当前页面是否为 `localhost` 或者 是否为 https 协议）。浏览器[限制](https://developer.mozilla.org/zh-CN/docs/Web/Security/Secure_Contexts/features_restricted_to_secure_contexts) `getUserMedia` 只能在安全上下文中使用。 |
| 为什么我的麦克风正常、摄像头也正常，但是设备没有正常工作? | 可能是设备权限未授予，详情可参考 [Web 排查设备权限获取失败问题](https://www.volcengine.com/docs/6348/1356355?s=g)。 |
| 接口调用时, 返回 "Invalid 'Authorization' header, Pls check your authorization header" 错误 | `Server/app.js` 中的 AK/SK 不正确 |
| 什么是 RTC | **R**eal **T**ime **C**ommunication, RTC 的概念可参考[官网文档](https://www.volcengine.com/docs/6348/66812?s=g)。 |
| 不清楚什么是主账号，什么是子账号 | 可以参考[官方概念](https://www.volcengine.com/docs/6257/64963?hyperlink_open_type=lark.open_in_browser&s=g) 。|
| 我有自己的服务端了, 我应该怎么让前端调用我的服务端呢 | 修改 `src/config/index.ts` 中的 `AIGC_PROXY_HOST` 请求域名和接口并在 `src/app/api.ts` 中修改接口参数配置 `APIS_CONFIG` |

如果有上述以外的问题，欢迎联系我们反馈。

### 相关文档
- [场景介绍](https://www.volcengine.com/docs/6348/1310537?s=g)
- [Demo 体验](https://www.volcengine.com/docs/6348/1310559?s=g)
- [场景搭建方案](https://www.volcengine.com/docs/6348/1310560?s=g)

## 更新日志

### OpenAPI 更新
参考 [OpenAPI 更新](https://www.volcengine.com/docs/6348/1544162) 中与 实时对话式 AI 相关的更新内容。

### Demo 更新

#### [1.6.0]
- 2025-09-30
    - 更新数字人场景相关配置
- 2025-07-08
    - 更新 RTC Web SDK 版本至 4.66.20
- 2025-06-26
    - 修复进房有问题的 BUG
- 2025-06-23
    - 简化 Demo 使用, 配置归一化。
    - 删除无用组件。
    - 追加服务端 README。
- 2025-06-18
    - 更新 RTC Web SDK 版本至 4.66.16
    - 更新 UI 和参数配置方式
    - 更新 Readme 文档
    - 追加 Node 服务的参数检测能力
    - 追加 Node 服务的 Token 生成能力
