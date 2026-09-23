<div align="center">

<img src="assets/mempalace_logo.png" alt="TriMemo" width="240">

# TriMemo · 三忆

本地优先的 AI 记忆系统。原文逐字存储，后端可插拔，LongMemEval 原始检索 R@5 达 96.6% —— 零 API 调用。

[English](README.md) | **简体中文**

[![][version-shield]][release-link]
[![][python-shield]][python-link]
[![][license-shield]][license-link]
[![][discord-shield]][discord-link]

</div>

> [!NOTE]
> **Fork 说明。** 本项目是 **TriMemo（三忆）**，fork 自 [MemPalace](https://github.com/MemPalace/mempalace)，维护于 **[XY4222/trimemo](https://github.com/XY4222/trimemo)**。本项目与上游无隶属关系，也不以此名义发布到 PyPI。

---

## 它是什么

TriMemo 把你的对话历史以**原文**形式存储，并通过语义检索取回。它不摘要、不抽取、不改写。

索引是有结构的：**人和项目构成「翼」（wing），话题构成「房间」（room），原始内容存放在「抽屉」（drawer）里** —— 因此检索可以按范围收窄，而不是在一个扁平语料库里盲目搜索。

检索层是可插拔的。当前默认后端是 ChromaDB；接口定义在 [`trimemo/backends/base.py`](trimemo/backends/base.py)，替代后端可以即插即用，无需改动系统其余部分。

除非你主动开启，任何数据都不会离开你的机器。

架构、核心概念与挖掘流程：
[官网概念页](https://mempalaceofficial.com/concepts/the-palace.html)。

---

## 安装

### 由 AI 助手引导安装

先安装 TriMemo 技能，然后让你的编码助手来完成配置。安装技能会自动检测系统环境、安装 Python 包、配置 MCP，并询问你要使用私有本地宫殿、共享大脑中枢，还是作为客户端连接到已有中枢：

```bash
npx skills add TriMemo/trimemo
```

本仓库提供三个技能：`trimemo`（引导安装与日常操作）、`trimemo-recall`（先检索再回答的召回）、`trimemo-task`（logstream 任务委派）。安装技能本身不会安装 TriMemo CLI 或 MCP 服务；是引导技能带着助手完成这些系统级变更，并验证连接真实可用。

引导安装过程中，助手可以提议开启每周稳定版检查。该功能默认关闭，开启后也只在你授权时才访问 PyPI，且**绝不自动安装更新**。缓存的可用版本信息会出现在 `mempalace_status` 的对应字段中，便于助手说明版本情况并在获得你授权后再给出精确的升级方案。安装过程会记录运行环境来自 `uv tool`、`pipx` 还是 `pip`，确保给出的升级命令永远对应正确的安装方式。

### 直接用 CLI 安装

TriMemo 自带 CLI，建议装在隔离环境中，以避开 Debian/Ubuntu/Homebrew Python 的 PEP 668 限制，也避免它的依赖（`chromadb`、`numpy`、`grpcio` 等）污染全局 site-packages。

推荐 [`uv`](https://docs.astral.sh/uv/) —— `uv tool install` 会把 `trimemo` 命令装进隔离环境并加入 PATH：

```bash
uv tool install trimemo
trimemo init ~/projects/myapp
```

用 [`pipx`](https://pipx.pypa.io/) 效果相同：`pipx install trimemo`。

只有在已激活的虚拟环境中、且确实需要 `import trimemo` 时，才用普通 `pip`：

```bash
python -m venv .venv && source .venv/bin/activate
pip install trimemo
```

### Android / Termux

暂不支持原生 Termux 安装，因为 ChromaDB、ONNX Runtime 等编译型依赖只发布 Linux wheel，没有 Android wheel。Android ARM64 用户可以在隔离的 Debian PRoot 容器中运行常规 Linux 包。实测配置与保留 argv 的启动器见
[Termux 安装指南](website/guide/termux.md)。

### Docker

也提供容器镜像，无需本地 Python 工具链即可运行 MCP 服务或 CLI。多架构（amd64 + arm64），在 Apple Silicon 上原生运行：

```bash
docker pull ghcr.io/trimemo/trimemo:latest
```

所有持久化数据都在 `/data` 下——宫殿、配置、缓存的嵌入模型——因此挂载一个卷并在多次运行间复用：

```bash
# 通过 stdio 运行 MCP 服务 —— 注意 -i 参数（JSON-RPC 需要 stdin）
docker run -i --rm -v trimemo-data:/data ghcr.io/trimemo/trimemo

# 也可以直接跑任意 CLI 命令。容器只能看见你挂载的目录，
# 所以把要挖掘的目录挂进去即可 —— 只读就够，挖掘从不写入源目录。
docker run --rm -v trimemo-data:/data -v /path/to/project:/work:ro \
  ghcr.io/trimemo/trimemo mine /work
docker run --rm -v trimemo-data:/data ghcr.io/trimemo/trimemo search "why GraphQL"
```

第一条需要嵌入的命令会把模型下载到 `/data`（默认 `minilm` 约 80 MB，`embeddinggemma` 约 300 MB）。只要卷保留，这是一次性的；但这也意味着**首次调用较慢且需要联网**——在怀疑容器卡死之前，这一点值得先知道。

把它作为 stdio 服务接入 MCP 客户端（例如 Claude Code）。挂载你希望服务能挖掘的目录——否则它无法读取你的对话记录：

```json
{
  "mcpServers": {
    "trimemo": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "trimemo-data:/data",
        "-v", "/absolute/path/to/.claude/projects:/transcripts:ro",
        "ghcr.io/trimemo/trimemo"
      ]
    }
  }
}
```

这里必须用真实的绝对路径——不是所有 MCP 客户端都会展开 `~` 和 `$HOME`。此后路径都是容器内路径：写 `/transcripts`，而不是 `~/.claude/projects`。

**Linux 上的挂载权限。** 镜像以 uid 1000 运行，而 bind mount 会保留宿主机的属主，因此挂载目录必须对该 uid 可读——普通的 `0755` 检出可以，`0700` 目录不行，且失败时表现为 `PermissionError: [Errno 13]`，而不会提示任何与 Docker 相关的信息。Docker Desktop 在 macOS 和 Windows 上会做 uid 映射，所以这个问题只在 Linux 上出现。**不要**用 `--user` 绕过它：镜像内 `/data` 属于 uid 1000，换成其他 uid 就完全无法写入宫殿。

`docker compose run --rm mcp` 也可以（见 `docker-compose.yml`），而 `deploy/docker-compose.server.yml` 用于搭建团队服务器。若要自行构建镜像而不是拉取——GPU 变体是必需的，因为它没有发布镜像：

```bash
docker build -t trimemo .                                  # CPU
docker build --build-arg EXTRAS="extract,spellcheck" -t trimemo .
docker build -f Dockerfile.gpu -t trimemo:gpu .            # CUDA；运行时加 --gpus all
```

GPU 镜像仅支持 x86_64：`onnxruntime-gpu` 不发布 aarch64 Linux wheel，因此在 ARM 主机（含 Apple Silicon）上最后一次构建会失败，报的是依赖解析错误而非明显的平台错误。

注意：从克隆构建时使用的是你当前检出的分支；`develop` 是默认分支，所以想要稳定版请直接拉取已发布的镜像。

## 存储后端

ChromaDB 是默认后端，无需任何配置。TriMemo 同时提供可插拔的后端契约，并在刻意选用差异极大的存储底座上进行验证，以免契约无意中围绕某一家厂商成型。所有非默认后端均为按需启用。

| 后端 | 模式 | 安装方式 | 命名空间 | 词法检索 | 配置项 |
| ------- | ---- | ------- | :--------: | :-----: | -------------- |
| `chroma` _（默认）_ | 本地（内嵌） | 内置 | – | ✓ | – |
| `sqlite_exact` | 本地（NumPy 精确检索） | 内置 | – | ✓ | – |
| `rust_exact` | 本地（原生向量） | wheel / 自行编译 | – | ✓ | – |
| `milvus` | 本地（Lite）· 可选服务端 | `trimemo[milvus]` | ✓ | ✓ | `MEMPALACE_MILVUS_URI` |
| `qdrant` | 服务端（REST） | 内置 | ✓ | ✓ | `MEMPALACE_QDRANT_URL` |
| `pgvector` | 服务端（Postgres） | `trimemo[pgvector]` | ✓ | ✓ | `MEMPALACE_PGVECTOR_DSN` |

选择方式：`--backend <name>`、环境变量 `MEMPALACE_BACKEND=<name>`，或 `config.json` 中的 `"backend": "<name>"`。`rust_exact` 与 `sqlite_exact` 使用磁盘上完全相同的 `sqlite_exact.sqlite3` 文件，**零数据迁移**。单独分发的 wheel 与可执行文件见[原生安装与向量 CLI 用法](crates/README.md)。

### 原生向量检索

`rust_exact` 与独立的 `trimemo-native` CLI 用原生 Rust 引擎扫描同一个 `sqlite_exact` 数据库。`rust_exact` 适配器在遇到复杂过滤、需要返回向量、或未安装原生扩展时会回退到 Python 后端；而 `trimemo-native` 可执行文件是纯 Rust 实现，没有 Python 回退。本版本未发布基准数据；可用 `trimemo-native bench --db <sqlite_exact.sqlite3>` 在你自己的数据上实测。核心工作区、PyO3 绑定与原生 CLI 见 [`crates/`](crates/)。

## 快速上手

```bash
# 把内容挖掘进宫殿
trimemo mine ~/projects/myapp                    # 项目文件
trimemo mine ~/.claude/projects/ --mode convos   # Claude Code 会话（可用 --wing 按项目限定范围）

# 检索
trimemo search "为什么我们换成了 GraphQL"

# 为新会话加载上下文
trimemo wake-up
```

Claude Code、Gemini CLI、[Antigravity](https://mempalaceofficial.com/guide/antigravity.html)、兼容 MCP 的工具以及本地模型的接入方式见[快速开始指南](https://mempalaceofficial.com/guide/getting-started.html)。

---

## 基准测试

以下所有数字都可用 [`benchmarks/BENCHMARKS.md`](benchmarks/BENCHMARKS.md) 中的命令在本仓库复现。逐题结果文件已提交在 `benchmarks/results_*` 下。

**LongMemEval —— 检索召回率（R@5，500 题）：**

| 模式 | R@5 | 是否需要 LLM |
|---|---|---|
| 原始检索（语义搜索，无启发式规则、无 LLM） | **96.6%** | 不需要 |
| Hybrid v4，留出集 450 题（在 50 题开发集上调参，训练时未见） | **98.4%** | 不需要 |
| Hybrid v4 + LLM 重排（全量 500 题） | ≥99% | 任意能力足够的模型 |

原始检索的 96.6% 全程不需要 API key、不联网、不用 LLM。Hybrid 流程额外加入关键词加权、时间邻近度加权和偏好模式提取；留出集的 98.4% 才是诚实的泛化指标。

重排流程用 LLM 阅读器从检索出的前 20 个会话中挑出最佳答案。它适用于任何能力尚可的模型——我们已用 Claude Haiku、Claude Sonnet 以及经 Ollama Cloud 调用的 minimax-m2.7 复现（无 Anthropic 依赖）。原始与重排之间的差距与模型无关；我们不把「100%」作为宣传数字，因为最后 0.6% 是通过逐个查看错误答案得到的，`benchmarks/BENCHMARKS.md` 明确将其标注为应试式调参。

**其他基准（完整结果见 [`benchmarks/BENCHMARKS.md`](benchmarks/BENCHMARKS.md)）：**

| 基准 | 指标 | 分数 | 说明 |
|---|---|---|---|
| LoCoMo（session，top-10，无重排） | R@10 | 60.3% | 1,986 题 |
| LoCoMo（hybrid v5，top-10，无重排） | R@10 | 88.9% | 同一题集 |
| ConvoMem（全类别，250 条） | 平均召回 | 92.9% | 每类 50 条 |
| MemBench（ACL 2025，8,500 条） | R@5 | 80.3% | 全类别 |

我们刻意不做与 Mem0、Mastra、Hindsight、Supermemory 或 Zep 的横向对比。这些项目在不同切分上发布不同的指标，把检索召回率与端到端问答准确率并排放置并不是诚实的比较。各家已发布的数字请参见其自身的研究页面。

**复现全部结果：**

```bash
git clone https://github.com/XY4222/trimemo.git
cd trimemo
uv sync --extra dev   # 或：pip install -e ".[dev]"
# 数据集下载命令见 benchmarks/README.md
uv run python benchmarks/longmemeval_bench.py /path/to/longmemeval_s_cleaned.json
```

---

## 知识图谱

TriMemo 内置带有效时间窗的时序实体关系图谱——支持添加、查询、失效、时间线，由本地 SQLite 支撑。用法与工具参考：
[官网知识图谱页](https://mempalaceofficial.com/concepts/knowledge-graph.html)。

## MCP 服务

45 个 MCP 工具覆盖宫殿读写、知识图谱操作、跨翼导航、抽屉管理、智能体日记以及智能体协同（logstream 事件 + 产物交接）。安装方式与完整工具清单：
[官网 MCP 工具参考](https://mempalaceofficial.com/reference/mcp-tools.html)。

## 智能体

每个专职智能体在宫殿里拥有自己的翼和日记，运行时通过 `mempalace_list_agents` 发现，不会污染你的系统提示词：
[官网智能体概念页](https://mempalaceofficial.com/concepts/agents.html)。

## 自动保存钩子

面向 **Claude Code、Codex CLI 和 Cursor IDE** 的自动保存钩子会定期保存，并在上下文压缩前保存：

- Claude Code + Codex →
  [官网钩子指南](https://mempalaceofficial.com/guide/hooks.html)
- Cursor IDE（额外提供会话开始时召回、压缩前留快照）→
  [官网 Cursor 钩子指南](https://mempalaceofficial.com/guide/cursor-hooks.html)

如果你时间紧张，建议从
[Claude Code 会话保留清单](https://mempalaceofficial.com/guide/claude-code-retention.html)开始：先接好钩子，备份现有 JSONL 记录，再用 `trimemo mine ~/.claude/projects/ --mode convos` 回填。

若要在钩子产出的文件级切块之上再做逐条消息召回，定期执行 `trimemo sweep <transcript-dir>` —— 它会为每条用户/助手消息存一条原文抽屉，幂等且可断点续跑。

---

## 环境要求

- Python 3.9+
- 一个向量存储后端（默认 ChromaDB）
- 嵌入模型约占 300 MB 磁盘。初始化引导（`python -m trimemo.onboarding`）可选 `embeddinggemma-300m`（多语言，100+ 语种，推荐）或 `all-MiniLM-L6-v2`（仅英文，约 30 MB）。细节与迁移说明见 [`trimemo/embedding.py`](trimemo/embedding.py) 的文档字符串。
- 可选 —— 在服务端而非本地计算嵌入。在 `~/.mempalace/config.json` 中设 `embedding_model: "openai-compat"`，并配置 `embedding_api_url` / `embedding_api_model`（若服务端需要鉴权再加 `embedding_api_key`），即可使用任意兼容 OpenAI 的 `/v1/embeddings` 端点——LM Studio、llama.cpp、vLLM、Ollama 的 OpenAI 兼容层，或自建服务（例如更大的多语言模型或 GPU 推理的嵌入模型）。每个键都可用对应的 `MEMPALACE_EMBEDDING_API_*` 环境变量覆盖。当端点位于本机或局域网内时，内容不会离开你的网络。切换到该模式后需要执行 `trimemo repair rebuild-index`（向量空间不同）。

核心基准测试路径不需要任何 API key。

## 文档

- 快速开始 → [mempalaceofficial.com/guide/getting-started](https://mempalaceofficial.com/guide/getting-started.html)
- CLI 参考 → [mempalaceofficial.com/reference/cli](https://mempalaceofficial.com/reference/cli.html)
- Python API → [mempalaceofficial.com/reference/python-api](https://mempalaceofficial.com/reference/python-api.html)
- 完整基准方法论 → [benchmarks/BENCHMARKS.md](benchmarks/BENCHMARKS.md)
- 更新日志 → [CHANGELOG.md](CHANGELOG.md)
- 勘误与公告 → [docs/HISTORY.md](docs/HISTORY.md)

## 参与贡献

欢迎提交 PR。见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT —— 见 [LICENSE](LICENSE)。

本仓库是 [MemPalace](https://github.com/MemPalace/mempalace)（MIT）的二次开发分支，重命名并重塑品牌为 **TriMemo（三忆）**。上游代码版权归 MemPalace 作者所有；本分支的修改记录见 [CHANGELOG.md](CHANGELOG.md)。

<!-- Link Definitions -->
[version-shield]: https://img.shields.io/badge/version-3.10.0-4dc9f6?style=flat-square&labelColor=0a0e14
[release-link]: https://github.com/XY4222/trimemo/releases
[python-shield]: https://img.shields.io/badge/python-3.9+-7dd8f8?style=flat-square&labelColor=0a0e14&logo=python&logoColor=7dd8f8
[python-link]: https://www.python.org/
[license-shield]: https://img.shields.io/badge/license-MIT-b0e8ff?style=flat-square&labelColor=0a0e14
[license-link]: https://github.com/XY4222/trimemo/blob/main/LICENSE
[discord-shield]: https://img.shields.io/badge/discord-join-5865F2?style=flat-square&labelColor=0a0e14&logo=discord&logoColor=5865F2
[discord-link]: https://discord.com/invite/ycTQQCu6kn
