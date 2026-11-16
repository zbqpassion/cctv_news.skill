# 新闻联播文字稿

取自 [央视网](https://tv.cctv.com/) 的文字稿。

👉👉👉 [目录](./INDEX.md) 👈👈👈

## 执行

需要 bun >= 1.1.29

```sh
bun install

# 只下载当天新闻文字稿
bun run fetch

# 重新创建 INDEX.md 索引文件
bun run make-index
```

## 构建

**bun 不需要构建**。

## 其他

代码最初源自 [xin-wen-lian-bo](https://github.com/DuckBurnIncense/xin-wen-lian-bo) 项目，感谢原作者的创造。

本项目在其基础上进行改进：

- 下载时同时保存源文件到 dump_htmls 目录，用于二次数据获取
- 支持 cctv 老版本 ui
- 升级依赖
- 删除文字稿正文中的 html 标签，生成的 markdown 有更好的可读性

## LICENSE

代码部分按 MIT License 发行。

## 重要声明

🚧🚧内容来自网络，版本归原作者，本项目仅用于研究学习。请不要用于奇怪的地方，后果自负🚧🚧

## 日报 Skill

仓库同时是一个 agent skill（见 [SKILL.md](./SKILL.md)）：基于 `news/` 里的文字稿生成《新闻联播》每日研判。文字稿归档照常每日更新，skill 只读取它。

- `scripts/check-report.py`：`facts YYYYMMDD` 输出当期条数、标题、链接等事实清单；`check YYYYMMDD 报告.md` 校验日报的结构、条数、链接和字数。
- `scripts/topics.py`：登记每期使用的长期主线和热词，保证跨天稳定可比（登记数据存放在本地 `state/`，不入库）。
- `scripts/trend-analysis.py`：按报道条数统计热词，`--until YYYYMMDD` 指定窗口截止日期。
- `scripts/manual-fetch.ts`：抓取指定日期的文字稿。
- `references/`：抓取逻辑与故障恢复流程。
- `deploy/agy-cctv-news.sh`：定时生成日报的包装脚本示例（先验证归档，再调用模型，最后校验）。
