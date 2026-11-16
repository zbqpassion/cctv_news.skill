import { fetchNews } from '../_fetch-news.ts';

const dateStr = process.argv[2];
if (!dateStr || !/^\d{8}$/.test(dateStr)) {
  console.error('Usage: bun manual-fetch.ts YYYYMMDD');
  process.exit(1);
}

const year = parseInt(dateStr.substring(0, 4));
const month = parseInt(dateStr.substring(4, 6)) - 1; // JS months are 0-indexed
const day = parseInt(dateStr.substring(6, 8));

console.log(`Manually fetching for ${dateStr} (${year}-${month + 1}-${day})...`);
fetchNews(new Date(year, month, day));
