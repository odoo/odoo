(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports) :
  typeof define === 'function' && define.amd ? define(['exports'], factory) :
  (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global.markedHighlight = {}));
})(this, (function (exports) { 'use strict';

  function markedHighlight(options) {
    if (typeof options === 'function') {
      options = {
        highlight: options
      };
    }

    if (!options || typeof options.highlight !== 'function') {
      throw new Error('Must provide highlight function');
    }

    if (typeof options.langPrefix !== 'string') {
      options.langPrefix = 'language-';
    }

    return {
      async: !!options.async,
      walkTokens(token) {
        if (token.type !== 'code') {
          return;
        }

        const lang = getLang(token.lang);

        if (options.async) {
          return Promise.resolve(options.highlight(token.text, lang, token.lang || '')).then(updateToken(token));
        }

        const code = options.highlight(token.text, lang, token.lang || '');
        if (code instanceof Promise) {
          throw new Error('markedHighlight is not set to async but the highlight function is async. Set the async option to true on markedHighlight to await the async highlight function.');
        }
        updateToken(token)(code);
      },
      useNewRenderer: true,
      renderer: {
        code(code, infoString, escaped) {
          // istanbul ignore next
          if (typeof code === 'object') {
            escaped = code.escaped;
            infoString = code.lang;
            code = code.text;
          }
          const lang = getLang(infoString);
          const classAttr = lang
            ? ` class="${options.langPrefix}${escape(lang)}"`
            : '';
          code = code.replace(/\n$/, '');
          return `<pre><code${classAttr}>${escaped ? code : escape(code, true)}\n</code></pre>`;
        }
      }
    };
  }

  function getLang(lang) {
    return (lang || '').match(/\S*/)[0];
  }

  function updateToken(token) {
    return (code) => {
      if (typeof code === 'string' && code !== token.text) {
        token.escaped = true;
        token.text = code;
      }
    };
  }

  // copied from marked helpers
  const escapeTest = /[&<>"']/;
  const escapeReplace = new RegExp(escapeTest.source, 'g');
  const escapeTestNoEncode = /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/;
  const escapeReplaceNoEncode = new RegExp(escapeTestNoEncode.source, 'g');
  const escapeReplacements = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  };
  const getEscapeReplacement = (ch) => escapeReplacements[ch];
  function escape(html, encode) {
    if (encode) {
      if (escapeTest.test(html)) {
        return html.replace(escapeReplace, getEscapeReplacement);
      }
    } else {
      if (escapeTestNoEncode.test(html)) {
        return html.replace(escapeReplaceNoEncode, getEscapeReplacement);
      }
    }

    return html;
  }

  exports.markedHighlight = markedHighlight;

}));
