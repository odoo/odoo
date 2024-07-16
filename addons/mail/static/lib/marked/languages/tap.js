/*! `tap` grammar compiled for Highlight.js 11.10.0 */
  (function(){
    var hljsGrammar = (function () {
  'use strict';

  /*
  Language: Test Anything Protocol
  Description: TAP, the Test Anything Protocol, is a simple text-based interface between testing modules in a test harness.
  Requires: yaml.js
  Author: Sergey Bronnikov <sergeyb@bronevichok.ru>
  Website: https://testanything.org
  */

  function tap(hljs) {
    return {
      name: 'Test Anything Protocol',
      case_insensitive: true,
      contains: [
        hljs.HASH_COMMENT_MODE,
        // version of format and total amount of testcases
        {
          className: 'meta',
          variants: [
            { begin: '^TAP version (\\d+)$' },
            { begin: '^1\\.\\.(\\d+)$' }
          ]
        },
        // YAML block
        {
          begin: /---$/,
          end: '\\.\\.\\.$',
          subLanguage: 'yaml',
          relevance: 0
        },
        // testcase number
        {
          className: 'number',
          begin: ' (\\d+) '
        },
        // testcase status and description
        {
          className: 'symbol',
          variants: [
            { begin: '^ok' },
            { begin: '^not ok' }
          ]
        }
      ]
    };
  }

  return tap;

})();

    hljs.registerLanguage('tap', hljsGrammar);
  })();