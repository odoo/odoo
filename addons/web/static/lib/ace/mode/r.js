/*
 * r.js
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
 *
 */
define(function(require, exports, module) {
   "use strict";

   var Range = require("../range").Range;
   var oop = require("../lib/oop");
   var TextMode = require("./text").Mode;
   var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;
   var RHighlightRules = require("./r_highlight_rules").RHighlightRules;
   var MatchingBraceOutdent = require("./matching_brace_outdent").MatchingBraceOutdent;
   var unicode = require("../unicode");

   var Mode = function()
   {
      this.HighlightRules = RHighlightRules;
      this.$outdent = new MatchingBraceOutdent();
   };
   oop.inherits(Mode, TextMode);

   (function()
   {
      this.lineCommentStart = "#";
      // todo import codeModel from RStudio
      /*this.tokenRe = new RegExp("^["
          + unicode.packages.L
          + unicode.packages.Mn + unicode.packages.Mc
          + unicode.packages.Nd
          + unicode.packages.Pc + "._]+", "g"
      );

      this.nonTokenRe = new RegExp("^(?:[^"
          + unicode.packages.L
          + unicode.packages.Mn + unicode.packages.Mc
          + unicode.packages.Nd
          + unicode.packages.Pc + "._]|\s])+", "g"
      );

      this.$complements = {
               "(": ")",
               "[": "]",
               '"': '"',
               "'": "'",
               "{": "}"
            };
      this.$reOpen = /^[(["'{]$/;
      this.$reClose = /^[)\]"'}]$/;

      this.getNextLineIndent = function(state, line, tab, tabSize, row)
      {
         return this.codeModel.getNextLineIndent(row, line, state, tab, tabSize);
      };

      this.allowAutoInsert = this.smartAllowAutoInsert;

      this.checkOutdent = function(state, line, input) {
         if (! /^\s+$/.test(line))
            return false;

         return /^\s*[\{\}\)]/.test(input);
      };

      this.getIndentForOpenBrace = function(openBracePos)
      {
         return this.codeModel.getIndentForOpenBrace(openBracePos);
      };

      this.autoOutdent = function(state, doc, row) {
         if (row == 0)
            return 0;

         var line = doc.getLine(row);

         var match = line.match(/^(\s*[\}\)])/);
         if (match)
         {
            var column = match[1].length;
            var openBracePos = doc.findMatchingBracket({row: row, column: column});

            if (!openBracePos || openBracePos.row == row) return 0;

            var indent = this.codeModel.getIndentForOpenBrace(openBracePos);
            doc.replace(new Range(row, 0, row, column-1), indent);
         }

         match = line.match(/^(\s*\{)/);
         if (match)
         {
            var column = match[1].length;
            var indent = this.codeModel.getBraceIndent(row-1);
            doc.replace(new Range(row, 0, row, column-1), indent);
         }
      };

      this.$getIndent = function(line) {
         var match = line.match(/^(\s+)/);
         if (match) {
            return match[1];
         }

         return "";
      };

      this.transformAction = function(state, action, editor, session, text) {
         if (action === 'insertion' && text === "\n") {

            // If newline in a doxygen comment, continue the comment
            var pos = editor.getSelectionRange().start;
            var match = /^((\s*#+')\s*)/.exec(session.doc.getLine(pos.row));
            if (match && editor.getSelectionRange().start.column >= match[2].length) {
               return {text: "\n" + match[1]};
            }
         }
         return false;
      };*/
       this.$id = "ace/mode/r";
   }).call(Mode.prototype);
   exports.Mode = Mode;
});
