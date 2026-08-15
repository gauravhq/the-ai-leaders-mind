// Drip publishing: a post gets its permanent /blog/<slug>/ URL only once its date has
// arrived. Future-dated posts render no page (and stay out of the listing, RSS feed, and
// sitemap) until the daily cron rebuild passes their date. Once live, the URL is permanent.
module.exports = {
  layout: "post.njk",
  tags: "posts",
  eleventyComputed: {
    permalink: (data) =>
      data.page.date.getTime() > Date.now() ? false : `/blog/${data.page.fileSlug}/`,
  },
};
