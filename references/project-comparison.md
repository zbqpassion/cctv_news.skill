# CCTV News Scraper Comparison

During the exploration of CCTV news transcript scrapers, three primary projects were identified:

1. **DuckBurnIncense/xin-wen-lian-bo** (Original)
   - Tech: Node.js, node-fetch.
   - Schedule: 20:30 CST (same day).
   - Output: Markdown with embedded HTML tags (raw `<p>`, `<div>`).
   - Link: https://github.com/DuckBurnIncense/xin-wen-lian-bo

2. **yuekcc/cctv_news** (Improved)
   - Tech: Bun, linkedom.
   - Schedule: 09:00 CST (next day).
   - Improvements: Strips HTML tags (clean Markdown), backs up source HTML in `dump_htmls/`, supports old CCTV UI.
   - Link: https://github.com/yuekcc/cctv_news

3. **zbqpassion/cctv_news.skill** (User-forked Skill)
   - Based on yuekcc/cctv_news.
   - Customized to run at 21:00 CST to capture current day data.
   - Modified `fetch-news.ts` to use `cnToday` instead of `yesterday` for fetching.
   - Link: https://github.com/zbqpassion/cctv_news.skill