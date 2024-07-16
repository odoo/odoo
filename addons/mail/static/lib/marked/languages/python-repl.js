/*! `python-repl` grammar compiled for Highlight.js 11.10.0 */
  (function(){
    var hljsGrammar = (function () {
  'use strict';

  /*
  Language: Python REPL
  Requires: python.js
  Author: Josh Goebel <hello@joshgoebel.com>
  Category: common
  */

  function pythonRepl(hljs) {
    return {
      aliases: [ 'pycon' ],
      contains: [
        {
          className: 'meta.prompt',
          starts: {
            // a space separates the REPL prefix from the actual code
            // this is purely for cleaner HTML output
            end: / |$/,
            starts: {
              end: '$',
              subLanguage: 'python'
            }
          },
          variants: [
            { begin: /^>>>(?=[ ]|$)/ },
            { begin: /^\.\.\.(?=[ ]|$)/ }
          ]
        }
      ]
    };
  }

  return pythonRepl;

})();

    hljs.registerLanguage('python-repl', hljsGrammar);
  })();