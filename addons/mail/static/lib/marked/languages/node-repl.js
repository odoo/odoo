/*! `node-repl` grammar compiled for Highlight.js 11.10.0 */
  (function(){
    var hljsGrammar = (function () {
  'use strict';

  /*
  Language: Node REPL
  Requires: javascript.js
  Author: Marat Nagayev <nagaevmt@yandex.ru>
  Category: scripting
  */

  /** @type LanguageFn */
  function nodeRepl(hljs) {
    return {
      name: 'Node REPL',
      contains: [
        {
          className: 'meta.prompt',
          starts: {
            // a space separates the REPL prefix from the actual code
            // this is purely for cleaner HTML output
            end: / |$/,
            starts: {
              end: '$',
              subLanguage: 'javascript'
            }
          },
          variants: [
            { begin: /^>(?=[ ]|$)/ },
            { begin: /^\.\.\.(?=[ ]|$)/ }
          ]
        }
      ]
    };
  }

  return nodeRepl;

})();

    hljs.registerLanguage('node-repl', hljsGrammar);
  })();