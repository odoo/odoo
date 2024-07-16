/*! `vbscript-html` grammar compiled for Highlight.js 11.10.0 */
  (function(){
    var hljsGrammar = (function () {
  'use strict';

  /*
  Language: VBScript in HTML
  Requires: xml.js, vbscript.js
  Author: Ivan Sagalaev <maniac@softwaremaniacs.org>
  Description: "Bridge" language defining fragments of VBScript in HTML within <% .. %>
  Website: https://en.wikipedia.org/wiki/VBScript
  Category: scripting
  */

  function vbscriptHtml(hljs) {
    return {
      name: 'VBScript in HTML',
      subLanguage: 'xml',
      contains: [
        {
          begin: '<%',
          end: '%>',
          subLanguage: 'vbscript'
        }
      ]
    };
  }

  return vbscriptHtml;

})();

    hljs.registerLanguage('vbscript-html', hljsGrammar);
  })();