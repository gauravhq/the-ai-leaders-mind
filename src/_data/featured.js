// Homepage "Featured this week": a weekly-rotating pick from the permanent post library.
// Every post stays live and indexable at /blog/<slug>/; this only chooses which ONE the homepage
// highlights this week. It advances by itself on the daily GitHub Actions rebuild, cycling through the
// whole library via week-number modulo N and repeating every N weeks (N = number of live posts), so the
// homepage stays weekly-fresh forever with no new content and no manual work. It rotates the HIGHLIGHT,
// not which pages exist. (BookHarness publishing model: all posts indexable, freshness via featured pick.)
const fs = require("fs");
const path = require("path");
const WEEK = 7 * 24 * 3600 * 1000;
const EPOCH = Date.parse("2025-08-15T00:00:00Z"); // week 0 = first post (one year before site launch); 200-week cycle starts here

module.exports = function () {
  const dir = path.join(__dirname, "..", "posts");
  const now = process.env.ROTATION_NOW ? Number(process.env.ROTATION_NOW) : Date.now();
  // Rotate only through posts whose date has ARRIVED (the live library); a future-dated post the author
  // adds later joins the rotation on its day. Stable filename order keeps the weekly sequence deterministic.
  const files = fs.readdirSync(dir)
    .filter((f) => /^\d{4}-\d{2}-\d{2}-.*\.md$/.test(f))
    .filter((f) => Date.parse(f.slice(0, 10) + "T00:00:00Z") <= now)
    .sort();
  const N = files.length;
  if (N === 0) return null;
  const wk = Math.floor((now - EPOCH) / WEEK);
  const f = files[((wk % N) + N) % N];
  const slug = f.replace(/^\d{4}-\d{2}-\d{2}-/, "").replace(/\.md$/, "");
  const raw = fs.readFileSync(path.join(dir, f), "utf8");
  const title = (raw.match(/title:\s*"([^"]*)"/) || [])[1] || slug;
  const description = (raw.match(/pageDescription:\s*"([^"]*)"/) || [])[1] || "";
  return { slug, title, description, url: `/blog/${slug}/`, week: wk, poolSize: N };
};
