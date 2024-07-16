/*! `clojure-repl` grammar compiled for Highlight.js 11.10.0 */
  (function(){
    var hljsGrammar = (function () {
  'use strict';

  /*
  Language: Clojure REPL
  Description: Clojure REPL sessions
  Author: Ivan Sagalaev <maniac@softwaremaniacs.org>
  Requires: clojure.js
  Website: https://clojure.org
  Category: lisp
  */

  /** @type LanguageFn */
  function clojureRepl(hljs) {
    return {
      name: 'Clojure REPL',
      contains: [
        {
          className: 'meta.prompt',
          begin: /^([\w.-]+|\s*#_)?=>/,
          starts: {
            end: /$/,
            subLanguage: 'clojure'
          }
        }
      ]
    };
  }

  return clojureRepl;

})();

    hljs.registerLanguage('clojure-repl', hljsGrammar);
  })();