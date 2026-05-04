import { fetchNews } from './_fetch-news.ts';

const today = new Date(); // 本地时间

// UTC+8 时间
const cnToday = new Date(
  Date.UTC(
    today.getUTCFullYear(),
    today.getUTCMonth(),
    today.getUTCDate(),
    today.getUTCHours(),
    today.getUTCMinutes() + 480,
    today.getUTCSeconds(),
  ),
);

// 获取当天的数据
fetchNews(cnToday);
