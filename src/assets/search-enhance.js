/* Rescue natural-language queries that Pagefind's strict AND matching drops to zero.
 *
 * Pagefind requires EVERY term to appear on a page. So "will i be replaced by AI in a few years?"
 * returns nothing, even though "replaced by AI" returns five good pages: the words "few" and "years"
 * never co-occur with the rest. People ask questions, so this is the common case, not the edge case.
 *
 * When the UI reports no results, this:
 *   1. strips filler words and punctuation,
 *   2. retries with progressively fewer, more distinctive terms (longest first),
 *   3. renders whatever it finds as "Closest matches",
 *   4. and if even that fails, offers real next steps instead of a dead end.
 *
 * Attach with SearchEnhance({ container, bundlePath, links }).
 */
(function () {
  var STOP = ("a an the and or but if then than that this these those is are was were be been being am "
    + "do does did doing have has had having i me my we our you your he him his she her it its they them "
    + "their what which who whom whose when where why how will would can could should shall may might must "
    + "of in on at by for with about against between into through during to from up down out off over under "
    + "again further once here there all any both each few more most other some such no nor not only own same "
    + "so too very just now get got make made go goes going want need really actually maybe perhaps ever never "
    + "am also because as until while about myself yourself does doesn dont don t s re ll ve"
  ).split(" ");
  var STOPSET = {};
  for (var i = 0; i < STOP.length; i++) STOPSET[STOP[i]] = true;

  function words(q) {
    return String(q || "").toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").split(/\s+/).filter(Boolean);
  }

  /* Keep 2-letter words: acronyms like "AI" are among the most distinctive terms on these sites. */
  function contentWords(q) {
    var seen = {};
    return words(q).filter(function (w) {
      if (STOPSET[w] || w.length < 2 || seen[w]) return false;
      seen[w] = true;
      return true;
    });
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  window.SearchEnhance = function (opts) {
    var container = typeof opts.container === "string"
      ? document.querySelector(opts.container) : opts.container;
    if (!container) return;
    var bundlePath = opts.bundlePath;
    var links = opts.links || [];
    var api = null, busy = false, lastTried = "";

    function pagefind() {
      if (!api) api = import(bundlePath + "pagefind.js");
      return api;
    }

    function panel() {
      var el = container.querySelector(".search-fallback");
      if (!el) {
        el = document.createElement("div");
        el.className = "search-fallback";
        container.appendChild(el);
      }
      return el;
    }

    function clearPanel() {
      var el = container.querySelector(".search-fallback");
      if (el) el.remove();
    }

    /* `brief` appends the next-steps row under partial results; without it this is the whole
       message for a query nothing matched at all. Either way the reader is never left at a dead end. */
    function suggestions(query, brief) {
      var html = brief
        ? '<p class="search-fallback__note">Still not it? Try a shorter phrase, or:</p>'
        : '<p class="search-fallback__note">Nothing on the site matches <strong>' + esc(query)
          + "</strong>. Try a shorter phrase, or start here:</p>";
      html += '<ul class="search-fallback__links">';
      for (var i = 0; i < links.length; i++) {
        html += '<li><a href="' + esc(links[i].url) + '">' + esc(links[i].label) + "</a></li>";
      }
      return html + "</ul>";
    }

    /* A question with no answer is a CONTENT signal, not just a dead end: it is the reader telling
       you what the FAQ or the blog is missing. A static site has no backend to log to, so report it
       to whichever privacy-light analytics the site already loads. Fires only if one is configured,
       so the default build sends nothing anywhere. */
    function reportGap(query) {
      try {
        if (typeof window.plausible === "function") {
          window.plausible("Search: no results", { props: { query: query } });
        } else if (typeof window.gtag === "function") {
          window.gtag("event", "search_no_results", { search_term: query });
        }
      } catch (e) { /* analytics must never break search */ }
    }

    async function rescue(query) {
      if (busy || query === lastTried) return;
      busy = true;
      lastTried = query;
      reportGap(query);
      try {
        var pf = await pagefind();
        var terms = contentWords(query).slice(0, 6);

        /* Pagefind is strict AND, so ONE unlucky word ("years") kills the whole query. Rather than
           guess which subset to keep, search each term on its own and rank pages by HOW MANY of the
           query's terms they match (classic coordination scoring). A page about being replaced by AI
           matches two terms and outranks a page that merely mentions years. */
        var perTerm = await Promise.all(terms.map(async function (t) {
          try {
            var r = await pf.search(t);
            var all = r ? r.results : [];
            return { term: t, total: all.length, hits: all.slice(0, 6) };
          } catch (e) { return { term: t, total: 0, hits: [] }; }
        }));

        /* Show a small group per word, in the order the reader typed them.
           Deliberately NOT a cleverer merged ranking: tried that, and purely statistical scoring
           cannot tell that "years" is incidental to this question while "replaced" is the point.
           Rarity ranked the throwaway word first; frequency ranked the generic hub pages first.
           Grouping is honest and predictable, and it puts the reader in charge of choosing. */
        var groups = perTerm.filter(function (p) { return p.hits.length; }).slice(0, 3);

        if (groups.length) {
          var html = '<p class="search-fallback__note">No page contains every word of <strong>'
            + esc(query) + "</strong>. Here is what each word finds:</p>";
          for (var g = 0; g < groups.length; g++) {
            var datas = await Promise.all(groups[g].hits.slice(0, 3).map(function (h) { return h.data(); }));
            html += '<p class="search-fallback__term">' + esc(groups[g].term)
              + ' <span>' + groups[g].total + (groups[g].total === 1 ? " page" : " pages") + "</span></p>"
              + '<ul class="search-fallback__results">';
            datas.forEach(function (doc) {
              html += '<li><a href="' + esc(doc.url) + '">'
                + esc((doc.meta && doc.meta.title) ? doc.meta.title : doc.url) + '</a><span>'
                + esc(String(doc.excerpt || "").replace(/<[^>]*>/g, "").slice(0, 110)) + "</span></li>";
            });
            html += "</ul>";
          }
          panel().innerHTML = html + suggestions(query, true);
          busy = false;
          return;
        }
        panel().innerHTML = suggestions(query);
      } catch (e) {
        panel().innerHTML = suggestions(query);
      }
      busy = false;
    }

    function currentQuery() {
      var input = container.querySelector(".pagefind-ui__search-input");
      return input ? input.value.trim() : "";
    }

    // The default UI does not expose a "no results" hook, so watch what it renders.
    var observer = new MutationObserver(function () {
      var msg = container.querySelector(".pagefind-ui__message");
      var hasResults = container.querySelector(".pagefind-ui__result");
      var q = currentQuery();
      if (!q) { clearPanel(); lastTried = ""; return; }
      if (hasResults) { clearPanel(); lastTried = ""; return; }
      if (msg && /^\s*no results/i.test(msg.textContent || "")) rescue(q);
    });
    observer.observe(container, { childList: true, subtree: true, characterData: true });
  };
})();
