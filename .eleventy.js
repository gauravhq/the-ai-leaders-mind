const { EleventyHtmlBasePlugin } = require("@11ty/eleventy");

module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
  // rewrites internal href/src to include the pathPrefix (project GitHub Pages site)
  eleventyConfig.addPlugin(EleventyHtmlBasePlugin);

  // Published posts are those whose date has ARRIVED. Future-dated posts stay hidden
  // until their day (the daily deploy cron re-publishes as dates arrive). Newest first.
  eleventyConfig.addCollection("posts", (api) => {
    const now = Date.now();
    return api
      .getFilteredByGlob("src/posts/*.md")
      .filter((p) => p.date.getTime() <= now)
      .sort((a, b) => b.date.getTime() - a.date.getTime());
  });

  eleventyConfig.addFilter("readableDate", (d) =>
    new Date(d).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" })
  );
  eleventyConfig.addFilter("isoDate", (d) => new Date(d).toISOString());
  eleventyConfig.addFilter("rssDate", (d) => new Date(d).toUTCString());
  eleventyConfig.addShortcode("year", () => String(new Date().getFullYear()));

  return {
    dir: { input: "src", output: "_site", includes: "_includes", data: "_data" },
    pathPrefix: process.env.PATH_PREFIX || "/the-ai-leaders-mind/",
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk",
  };
};
