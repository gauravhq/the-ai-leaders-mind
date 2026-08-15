// Every post is a permanent, indexable page (SEO). All live at /blog/<slug>/.
module.exports = {
  layout: "post.njk",
  tags: "posts",
  eleventyComputed: {
    permalink: (data) => `/blog/${data.page.fileSlug}/`,
  },
};
