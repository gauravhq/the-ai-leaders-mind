/* Closest matches for question-shaped searches. There is no "no results" state.
 *
 * Pagefind matches strict AND, so every word must appear on one page. Readers type questions, so an
 * exact match is the exception, not the rule: "will i be replaced by AI in a few years?" finds
 * nothing, even though the FAQ literally answers "Will AI replace managers and leaders?".
 *
 * When the index has no exact hit this shows, in order:
 *   1. CLOSEST QUESTIONS  matched question-to-question against the FAQ bank (/search-faq.json).
 *      The FAQ is a bank of questions and the reader typed a question, so this is the most direct
 *      comparison available, and it deep-links to the single answer.
 *   2. CLOSEST PAGES      each meaningful word searched on its own, then merged and ranked by
 *      Pagefind's own relevance score weighted by how rare the word is, how many of the query's
 *      words the page covers, and whether the word is in the title.
 *   3. NEXT STEPS         FAQ / all posts / the book, so nothing ever dead-ends.
 *
 * Attach with SearchEnhance({ container, bundlePath, faqIndex, links }).
 */
(function () {
  var STOP = ("a an the and or but if then than that this these those is are was were be been being am "
    + "do does did doing have has had having i me my we our you your he him his she her it its they them "
    + "their what which who whom whose when where why how will would can could should shall may might must "
    + "of in on at by for with about against between into through during to from up down out off over under "
    + "again further once here there all any both each few more most other some such no nor not only own same "
    + "so too very just now get got make made go goes going want need really actually maybe perhaps ever never "
    + "also because as until while myself yourself dont don t s re ll ve im ive"
  ).split(" ");
  var STOPSET = {};
  for (var i = 0; i < STOP.length; i++) STOPSET[STOP[i]] = true;

  /* Crude suffix stripping so "replaced", "replace" and "replacing" collide. Deliberately gentle:
     a real stemmer is not worth shipping, and over-stemming creates nonsense matches. */
  function stem(w) {
    if (w.length <= 4) return w;
    w = w.replace(/(ations|ation|ingly|ing|edly|ed|ies|ly|es|s)$/, "");
    /* Also drop a trailing "e", or the halves never meet: the reader's "replaced" reduces to
       "replac" while the FAQ's "replace" stays whole, and the one question that answers them
       ("Will AI replace managers and leaders?") is missed. */
    return w.replace(/e$/, "");
  }

  function tokens(q) {
    var raw = String(q || "").toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").split(/\s+/);
    var out = [], seen = {};
    for (var i = 0; i < raw.length; i++) {
      var w = raw[i];
      if (!w || STOPSET[w] || w.length < 2) continue;
      if (seen[w]) continue;
      seen[w] = true;
      out.push(w);
    }
    return out;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* Build the scored question bank once: document frequencies over the QUESTION corpus, so a word
     common to many questions ("ai") counts for less than a rare one ("replace"). Kept at module
     scope, and exposed below, so the matcher can be batch-tested against real reader questions
     rather than a copy of itself that is free to drift. */
  function buildQuestionBank(rows) {
    var df = {}, entries = (rows || []).map(function (row) {
      var t = tokens(row.q).map(stem), uniq = {};
      t.forEach(function (w) { uniq[w] = true; });
      Object.keys(uniq).forEach(function (w) { df[w] = (df[w] || 0) + 1; });
      return { q: row.q, a: row.a, url: row.url, topic: row.topic, terms: uniq, len: t.length || 1 };
    });
    return { entries: entries, df: df, n: entries.length };
  }

  function matchQuestions(bank, query) {
    var qt = tokens(query).map(stem);
    if (!qt.length || !bank.entries.length) return [];
    var scored = bank.entries.map(function (e) {
      var s = 0, hits = 0;
      for (var i = 0; i < qt.length; i++) {
        if (e.terms[qt[i]]) {
          s += Math.log(1 + bank.n / (1 + (bank.df[qt[i]] || 0)));   // rarer word, more signal
          hits++;
        }
      }
      // normalise by question length so a long question does not win just by having more words
      return { e: e, score: hits ? s / Math.sqrt(e.len) : 0, hits: hits };
    }).filter(function (x) { return x.hits > 0; })
      .sort(function (a, b) { return b.score - a.score; });

    if (!scored.length) return [];
    /* Show up to FIVE options, not one. Measured against 20 real reader questions: the top-ranked
       question is right about half the time, but a genuinely useful one is in the top few far more
       often ("is my job safe from AI?" ranks the right answer 2nd, "am i getting worse at my job?"
       3rd). No lexical score can tell that "safe" is incidental and "job" is the topic, so the honest
       answer is to present the closest OPTIONS and let the reader pick. The relative cutoff still
       drops anything far behind the leader, so weak noise is not padded in to reach five. */
    var best = scored[0].score;
    return scored.filter(function (x) { return x.score >= best * 0.45; }).slice(0, 5).map(function (x) { return x.e; });
  }

  window.SearchEnhance = function (opts) {
    var container = typeof opts.container === "string"
      ? document.querySelector(opts.container) : opts.container;
    if (!container) return;
    var bundlePath = opts.bundlePath;
    var faqIndexUrl = opts.faqIndex;
    var links = opts.links || [];
    var api = null, faq = null, busy = false, lastTried = "";

    function pagefind() {
      if (!api) api = import(bundlePath + "pagefind.js");
      return api;
    }

    /* Load the question bank once, and precompute document frequencies over the QUESTIONS so a word
       common to many questions ("ai") counts for less than a rare one ("replace"). */
    function faqBank() {
      if (faq) return faq;
      faq = fetch(faqIndexUrl)
        .then(function (r) { return r.json(); })
        .then(buildQuestionBank)
        .catch(function () { return { entries: [], df: {}, n: 0 }; });
      return faq;
    }

    async function closestPages(pf, query) {
      var terms = tokens(query).slice(0, 6);
      if (!terms.length) return { docs: [], terms: [] };

      var per = await Promise.all(terms.map(async function (t) {
        try {
          var r = await pf.search(t);
          return { term: t, total: r ? r.results.length : 0, hits: r ? r.results.slice(0, 8) : [] };
        } catch (e) { return { term: t, total: 0, hits: [] }; }
      }));

      var matched = per.filter(function (p) { return p.hits.length; });
      if (!matched.length) return { docs: [], terms: [] };

      var docs = {};
      for (var j = 0; j < matched.length; j++) {
        var p = matched[j];
        /* Weight the word by rarity. Used ALONE this misleads (a throwaway word can be the rarest),
           which is why it only ever multiplies Pagefind's own relevance score below. */
        var idf = 1 / Math.log(2 + p.total);
        var datas = await Promise.all(p.hits.map(function (h) { return h.data(); }));
        for (var d = 0; d < datas.length; d++) {
          var doc = datas[d], key = doc.url;
          if (!docs[key]) {
            docs[key] = {
              url: doc.url,
              title: (doc.meta && doc.meta.title) ? doc.meta.title : doc.url,
              excerpt: String(doc.plain_excerpt || doc.excerpt || "").replace(/<[^>]*>/g, ""),
              score: 0, covered: 0
            };
          }
          var titleBoost = (docs[key].title || "").toLowerCase().indexOf(p.term) >= 0 ? 1.6 : 1;
          docs[key].score += (p.hits[d].score || 1) * idf * titleBoost;
          docs[key].covered += 1;
        }
      }

      var list = Object.keys(docs).map(function (k) { return docs[k]; });
      list.forEach(function (x) {
        // a page answering MORE of the question beats one that merely repeats a single word
        x.score *= (1 + 0.5 * (x.covered - 1));
      });
      list.sort(function (a, b) { return b.score - a.score; });
      return { docs: list.slice(0, 5), terms: matched.map(function (m) { return m.term; }) };
    }

    function nextSteps(lead) {
      var html = '<p class="search-fallback__note">' + lead + "</p>" + '<ul class="search-fallback__links">';
      for (var i = 0; i < links.length; i++) {
        html += '<li><a href="' + esc(links[i].url) + '">' + esc(links[i].label) + "</a></li>";
      }
      return html + "</ul>";
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

    /* A question with no answer is a CONTENT signal: the reader is telling you what the FAQ is
       missing. Reported to whichever privacy-light analytics the site already loads, and nothing is
       sent when none is configured, which is the default. */
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
        var bank = faqIndexUrl ? await faqBank() : { entries: [], df: {}, n: 0 };
        var questions = matchQuestions(bank, query);

        var pf = await pagefind();
        var pages = await closestPages(pf, query);

        var html = "";
        if (questions.length || pages.docs.length) {
          html += '<p class="search-fallback__note">No page matches every word of <strong>'
            + esc(query) + "</strong>. Here is the closest the site has:</p>";
        }

        if (questions.length) {
          html += '<p class="search-fallback__term">Closest questions</p><ul class="search-fallback__results">';
          questions.forEach(function (e) {
            html += '<li><a href="' + esc(e.url) + '">' + esc(e.q) + "</a><span>"
              + esc(String(e.a || "").slice(0, 120)) + "</span></li>";
          });
          html += "</ul>";
        }

        if (pages.docs.length) {
          html += '<p class="search-fallback__term">Closest pages <span>matching '
            + esc(pages.terms.join(", ")) + "</span></p><ul class=\"search-fallback__results\">";
          pages.docs.forEach(function (d) {
            html += '<li><a href="' + esc(d.url) + '">' + esc(d.title) + "</a><span>"
              + esc(d.excerpt.slice(0, 120)) + "</span></li>";
          });
          html += "</ul>";
        }

        panel().innerHTML = html
          ? html + nextSteps("Still not it? Try a shorter phrase, or:")
          : nextSteps("Nothing on the site matches <strong>" + esc(query) + "</strong>. Try a shorter phrase, or:");
      } catch (e) {
        panel().innerHTML = nextSteps("Search hit a problem. Try:");
      }
      busy = false;
    }

    function currentQuery() {
      var input = container.querySelector(".pagefind-ui__search-input");
      return input ? input.value.trim() : "";
    }

    // the default UI exposes no "no results" hook, so watch what it renders
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

  // exposed so the matcher can be batch-tested against real reader questions (checklist 25 item 14k6)
  window.SearchEnhance.buildQuestionBank = buildQuestionBank;
  window.SearchEnhance.matchQuestions = matchQuestions;
  window.SearchEnhance.tokens = tokens;
  window.SearchEnhance.stem = stem;
})();
