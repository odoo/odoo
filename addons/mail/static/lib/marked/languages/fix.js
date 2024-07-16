/*! `fix` grammar compiled for Highlight.js 11.10.0 */
  (function(){
    var hljsGrammar = (function () {
  'use strict';

  /*
  Language: FIX
  Author: Brent Bradbury <brent@brentium.com>
  */

  /** @type LanguageFn */
  function fix(hljs) {
    return {
      name: 'FIX',
      contains: [
        {
          begin: /[^\u2401\u0001]+/,
          end: /[\u2401\u0001]/,
          excludeEnd: true,
          returnBegin: true,
          returnEnd: false,
          contains: [
            {
              begin: /([^\u2401\u0001=]+)/,
              end: /=([^\u2401\u0001=]+)/,
              returnEnd: true,
              returnBegin: false,
              className: 'attr'
            },
            {
              begin: /=/,
              end: /([\u2401\u0001])/,
              excludeEnd: true,
              excludeBegin: true,
              className: 'string'
            }
          ]
        }
      ],
      case_insensitive: true
    };
  }

  return fix;

})();

    hljs.registerLanguage('fix', hljsGrammar);
  })();