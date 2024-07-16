/*! `parser3` grammar compiled for Highlight.js 11.10.0 */
  (function(){
    var hljsGrammar = (function () {
  'use strict';

  /*
  Language: Parser3
  Requires: xml.js
  Author: Oleg Volchkov <oleg@volchkov.net>
  Website: https://www.parser.ru/en/
  Category: template
  */

  function parser3(hljs) {
    const CURLY_SUBCOMMENT = hljs.COMMENT(
      /\{/,
      /\}/,
      { contains: [ 'self' ] }
    );
    return {
      name: 'Parser3',
      subLanguage: 'xml',
      relevance: 0,
      contains: [
        hljs.COMMENT('^#', '$'),
        hljs.COMMENT(
          /\^rem\{/,
          /\}/,
          {
            relevance: 10,
            contains: [ CURLY_SUBCOMMENT ]
          }
        ),
        {
          className: 'meta',
          begin: '^@(?:BASE|USE|CLASS|OPTIONS)$',
          relevance: 10
        },
        {
          className: 'title',
          begin: '@[\\w\\-]+\\[[\\w^;\\-]*\\](?:\\[[\\w^;\\-]*\\])?(?:.*)$'
        },
        {
          className: 'variable',
          begin: /\$\{?[\w\-.:]+\}?/
        },
        {
          className: 'keyword',
          begin: /\^[\w\-.:]+/
        },
        {
          className: 'number',
          begin: '\\^#[0-9a-fA-F]+'
        },
        hljs.C_NUMBER_MODE
      ]
    };
  }

  return parser3;

})();

    hljs.registerLanguage('parser3', hljsGrammar);
  })();