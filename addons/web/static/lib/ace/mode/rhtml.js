/*
 * rhtml.js
 *
 * Copyright (C) 2009-11 by RStudio, Inc.
 *
 * The Initial Developer of the Original Code is
 * Ajax.org B.V.
 * Portions created by the Initial Developer are Copyright (C) 2010
 * the Initial Developer. All Rights Reserved.
 *
 * Distributed under the BSD license:
 *
 * Copyright (c) 2010, Ajax.org B.V.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *     * Neither the name of Ajax.org B.V. nor the
 *       names of its contributors may be used to endorse or promote products
 *       derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL AJAX.ORG B.V. BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 */

define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var HtmlMode = require("./html").Mode;

var RHtmlHighlightRules = require("./rhtml_highlight_rules").RHtmlHighlightRules;
/* Make life easier, don't do these right now 
var SweaveBackgroundHighlighter = require("mode/sweave_background_highlighter").SweaveBackgroundHighlighter;
var RCodeModel = require("mode/r_code_model").RCodeModel;
*/

var Mode = function(doc, session) {
   HtmlMode.call(this);
   this.$session = session;
   this.HighlightRules = RHtmlHighlightRules;

   /* Or these.
   this.codeModel = new RCodeModel(doc, this.$tokenizer, /^r-/,
                                   /^<!--\s*begin.rcode\s*(.*)/);
   this.foldingRules = this.codeModel;
   this.$sweaveBackgroundHighlighter = new SweaveBackgroundHighlighter(
         session,
         /^<!--\s*begin.rcode\s*(?:.*)/,
         /^\s*end.rcode\s*-->/,
         true); */
};
oop.inherits(Mode, HtmlMode);

(function() {
   this.insertChunkInfo = {
      value: "<!--begin.rcode\n\nend.rcode-->\n",
      position: {row: 0, column: 15}
   };
    
   this.getLanguageMode = function(position)
   {
      return this.$session.getState(position.row).match(/^r-/) ? 'R' : 'HTML';
   };

   /* this.getNextLineIndent = function(state, line, tab, tabSize, row)
   {
      return this.codeModel.getNextLineIndent(row, line, state, tab, tabSize);
   }; */

    this.$id = "ace/mode/rhtml";
}).call(Mode.prototype);

exports.Mode = Mode;
});
