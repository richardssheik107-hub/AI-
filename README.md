# 基于火山引擎 RTC 与 RAG 的实时语音智能客服系统

这是一个面向信用卡与消费金融客服场景的实时语音智能客服项目，基于开源 Demo `ark_aigc_demo` 二次开发。项目完成了从用户语音输入、RTC 实时传输、ASR 识别、CustomLLM 回调、自定义 RAG 检索、豆包大模型生成，到 TTS 语音播报的完整闭环。

项目目标是把一个官方 AIGC Demo 改造成可用于实习简历展示的工程项目：不仅能跑通实时语音对话，还能讲清楚 RAG、RTC、ASR/TTS、回调调试和服务端工程化。

## 项目亮点

- 使用 React + 火山 RTC SDK 实现实时语音通话和字幕展示。
- 使用 FastAPI 搭建自定义 AI 后端，接收火山 `CustomLLM` 回调。
- 接入火山知识库，实现信用卡与消费金融场景下的 RAG 检索增强。
- 使用 OpenAI Chat Completions 兼容 SSE 响应，让 RTC 云端可以流式消费 LLM 输出。
- 通过 NATAPP 将本地 RAG 服务映射到公网，解决云端回调本地服务的调试问题。
- 支持 `/debug/rag`、`/debug/chat`、`/health` 等调试接口，方便面试演示和链路排障。
- 支持配置知识库检索条数和上下文长度，并在调试接口中返回命中片段、耗时和上下文长度，便于优化 RAG 召回质量。

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

## RTC 语音链路拆解

本项目没有把用户语音通过 WebSocket 或 HTTP 上传到自己的后端，而是使用 RTC 作为实时媒体通道。后端只负责鉴权、启动云端 Agent 和 CustomLLM 回调，音频流本身由火山 RTC 云端处理，降低了本地服务的带宽和转发压力。

### 1. 用户加入 RTC 房间

前端调用 `RtcClient.joinRoom()` 加入房间，核心代码在 `src/lib/RtcClient.ts`。加入房间时配置了 `isAutoSubscribeAudio: true`，因此 AI Agent 后续发布音频流时，浏览器可以自动订阅并播放。

### 2. 麦克风采集与用户音频推流

麦克风采集由 RTC SDK 处理，入口是 `RtcClient.startAudioCapture()`。用户开启麦克风后，前端通过 `RtcClient.publishStream(MediaType.AUDIO)` 将本地音频发布到 RTC 房间，代码调用链主要在 `src/lib/useCommon.ts` 和 `src/lib/RtcClient.ts`。

### 3. ASR 字幕与 AI 回复文本

用户说话后的字幕不是前端本地识别的，而是云端 ASR 识别后通过 RTC 二进制消息回传。前端在 `src/lib/RtcClient.ts` 注册 `onRoomBinaryMessageReceived`，再由 `src/lib/listenerHooks.ts` 的 `handleRoomBinaryMessageReceived` 调用 `src/utils/handler.ts` 解析消息。

`src/utils/handler.ts` 中的 `MESSAGE_TYPE.SUBTITLE = 'subv'` 对应字幕消息，既可能是用户 ASR 文本，也可能是 AI 的 LLM 回复文本。前端通过消息里的 `userId` 区分“我”和“AI”。

### 4. AI 回复语音播放

AI 的文字回复由云端 TTS 合成为音频，AI Agent 像一个远端用户一样在 RTC 房间里发布音频流。前端通过 `onUserPublishStream` 监听到远端音频发布，处理逻辑在 `src/lib/listenerHooks.ts` 的 `handleUserPublishStream`。

如果浏览器阻止自动播放，RTC SDK 会触发 `onAutoplayFailed`，前端可以提示用户点击页面恢复播放。

### 5. 打断与控制指令

项目的打断不是走普通 HTTP 请求，而是通过 RTC 二进制消息发送给云端 Agent。前端 `AudioController` 调用 `RtcClient.commandAgent()`，内部使用 `sendUserBinaryMessage` 发送控制指令，相关代码在 `src/pages/MainPage/MainArea/Room/AudioController.tsx` 和 `src/lib/RtcClient.ts`。

这也是使用 RTC 的核心价值之一：音频流、字幕消息和控制指令都在低延迟实时链路里完成，更适合语音对话里的“边听边说”和“随时打断”。

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
- `KB_SEARCH_LIMIT` 用于控制知识库召回条数，`KB_MAX_CONTEXT_CHARS` 用于限制传给 LLM 的知识库上下文长度。
- 使用 NATAPP 免费 HTTP 隧道时，代码会在 `LLMConfig` 中携带 `Feature: "{\"Http\":true}"`。

## 启动步骤

推荐使用一键启动脚本，它会自动打开三个 PowerShell 窗口，分别启动 RAG 后端、NATAPP 和前端。

### 双击启动

在项目根目录直接双击：

```text
start-dev.bat
```

如果 NATAPP 已经保存过 token，弹窗里直接回车即可；如果没有保存，就输入 NATAPP 隧道 token 后回车。

### PowerShell 启动

```powershell
cd C:\Users\Fergeson\Desktop\AI智能语音客服\ark_aigc_demo
.\scripts\start-dev.ps1 -NatappToken 你的隧道token
```

如果 NATAPP 已经保存过 token，也可以直接运行：

```powershell
.\scripts\start-dev.ps1
```

启动后打开：

```text
http://localhost:3000
```

NATAPP 请求检查面板：

```text
http://127.0.0.1:4040
```

如果 NATAPP 输出了新的公网地址，需要把 `.env` 中的 `SERVER_URL` 改成新地址，并重启 RAG 后端窗口。

### 手动启动

如果不用脚本，则需要同时保持三个窗口运行。

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
GET http://localhost:3001/debug/rag?query=信用卡晚还一天会不会影响征信
```

用于确认火山知识库检索是否正常。接口会返回 `items` 命中明细、`used_blocks`、`length` 和 `duration_ms`，方便判断知识库是否命中正确片段。

也可以临时指定检索条数：

```text
GET http://localhost:3001/debug/rag?query=信用卡晚还一天会不会影响征信&limit=2
```

### 文本问答调试

```text
POST http://localhost:3001/debug/chat
```

请求体示例：

```json
{
  "history": [],
  "question": "信用卡只还最低还款会怎么样？"
}
```

### 完整链路调试

```text
POST http://localhost:3001/debug/chat/full
```

用于排查完整 RAG + LLM 链路。接口会返回用户问题、RAG 命中条数、命中片段、上下文长度、RAG 耗时、LLM 首 token 时间、LLM 总耗时和最终回答。

请求体示例：

```json
{
  "history": [],
  "question": "信用卡晚还一天会不会影响征信？"
}
```

## 评测集闭环

项目内置了一个金融客服评测集，用来验证 Prompt、RAG 和合规边界是否稳定。题库位置：

```text
rag_llm_server/evals/eval_cases.json
```

本地批量评测脚本：

```powershell
cd C:\Users\Fergeson\Desktop\AI智能语音客服\ark_aigc_demo\rag_llm_server
.\.venv\Scripts\python.exe .\evals\run_eval.py --limit 3
```

运行全部题目：

```powershell
.\.venv\Scripts\python.exe .\evals\run_eval.py
```

只复测某一条：

```powershell
.\.venv\Scripts\python.exe .\evals\run_eval.py --case-id cc_credit_late_one_day
```

测试敏感信息拦截：

```powershell
.\.venv\Scripts\python.exe .\evals\run_eval.py --case-id sensitive_sms_code --markdown
```

验证 RAG 缓存效果，并生成 Markdown 报告：

```powershell
.\.venv\Scripts\python.exe .\evals\run_eval.py --limit 3 --repeat 2 --markdown
```

评测脚本会调用 `/debug/chat/full`，输出每条问题的安全拦截/FAQ/RAG 路径、RAG 候选召回数、重排后命中条数、缓存命中状态、上下文长度、首 token 时间、最终回答和规则检查结果。报告会保存到 `outputs/evals/`，该目录不会提交到 GitHub。

评测结果如果失败，需要按下面顺序判断：

1. `rag.item_count` 为 0：优先优化知识库内容、切片或检索关键词。
2. RAG 命中正常但回答不合规：优先优化 Prompt 或安全规则。
3. 敏感信息问题没有走 `safety_direct`：优先补充 `services/compliance_service.py` 中的规则。
4. `rag.cache_hit` 一直为 `false`：确认是否使用了相同问题、缓存 TTL 是否过短，或后端是否重启导致内存缓存清空。
5. `rag.candidate_item_count` 有多条但 `items` 排序不准：优先调整知识库切片、关键词，或切换到外部 rerank 模型。
6. `first_token_ms` 或总耗时过高：调整 `KB_SEARCH_LIMIT`、`KB_MAX_CONTEXT_CHARS`、`ARK_MAX_TOKENS` 和模型低延迟参数。

### CustomLLM 回调接口

```text
POST http://localhost:3001/api/chat_callback
```

火山 RTC 云端会请求该接口。接口返回 `text/event-stream`，并以 `data: [DONE]` 结束。

## 排障路径

如果前端显示“AI 准备中”或 AI 无回复，按下面顺序定位：

1. 打开 `http://127.0.0.1:4040`，确认 NATAPP/ngrok 是否收到 `POST /api/chat_callback`。
2. 检查前端控制台或后端日志，确认 `StartVoiceChat` 是否返回 `ok`。
3. 访问 `/health`，确认 RTC、ASR、TTS、Ark、知识库和 `SERVER_URL` 配置齐全。
4. 访问 `/debug/rag?query=你的问题&limit=2`，确认知识库是否命中正确片段。
5. 调用 `/debug/chat/full`，确认 RAG、LLM、首 token 和总耗时是否正常。
6. 如果 `/debug/chat/full` 正常但语音无回复，优先检查 RTC 云端是否回调、SSE 是否以 `data: [DONE]` 结束，以及浏览器是否允许音频播放。

## 面试讲法

可以用下面这段概括项目：

```text
我基于火山引擎 RTC 和豆包大模型实现了一个面向信用卡与消费金融业务的实时语音智能客服系统。前端通过 RTC SDK 采集并发布用户语音，云端 Agent 完成 ASR 识别后，通过 CustomLLM 回调我的 FastAPI RAG 后端。后端检索火山知识库，把检索结果合并进系统提示词，再调用豆包模型流式生成回答，最后由云端 TTS 合成为语音并通过 RTC 播放给用户。
```

重点可以展开：

- 为什么使用 RTC：低延迟、弱网优化、音频 3A、支持打断。
- RAG 如何接入：`CustomLLM.Url` 回调到 FastAPI，后端检索知识库后调用 LLM。
- 如何调试：`/health` 看配置，`/debug/rag` 看检索命中、上下文长度和耗时，NATAPP 暴露公网回调。
- 如何排障：`/debug/chat/full` 返回 RAG + LLM 完整链路信息，结合 NATAPP 4040 面板判断火山云端是否打到本地服务。
- RAG 如何优化：通过 `KB_SEARCH_LIMIT` 控制召回条数，通过 `KB_MAX_CONTEXT_CHARS` 控制传给 LLM 的上下文长度，平衡准确率、延迟和 token 成本。
- 如何评测：用 `rag_llm_server/evals/run_eval.py` 跑金融客服 Golden Dataset，检查征信、盗刷、投诉、验证码等高风险场景是否合规。
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
