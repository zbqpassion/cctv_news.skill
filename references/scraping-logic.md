# CCTV News Scraping Logic

## URL Structure
- **Daily List**: `http://tv.cctv.com/lm/xwlb/day/{YYYYMMDD}.shtml`
- **Detailed News**: Individual links found within the list HTML.

## DOM Selectors
- **List Links**: `a` nodes within the list page. The first link is usually the **Abstract/Summary**.
- **News Title**: `#page_body > div.allcontent > div.video18847 > div.playingVideo > div.tit` (Remove `[视频]` suffix).
- **News Content**: `#content_area`
- **Abstract/Summary**: `#page_body > div.allcontent > div.video18847 > div.playingCon > div.nrjianjie_shadow > div > ul > li:nth-child(1) > p`

## UI Versions
- **New UI**: Modern CSS selectors above.
- **Old UI**: The `yuekcc` fork contains fallback logic to handle legacy CCTV page layouts.

## Clean-up Logic
To convert HTML to clean Markdown, use the following `unified` pipeline:
1. `rehype-parse`
2. `rehype-remark`
3. `remark-gfm`
4. `remark-stringify`
