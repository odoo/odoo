/* ***** BEGIN LICENSE BLOCK *****
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
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * ***** END LICENSE BLOCK ***** */

define(function(require, exports, module) {
"use strict";

var oop = require("../lib/oop");
var DocCommentHighlightRules = require("./doc_comment_highlight_rules").DocCommentHighlightRules;
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var leanHighlightRules = function() {

    var keywordControls = (
        [ "add_rewrite", "alias", "as", "assume", "attribute",
          "begin", "by", "calc", "calc_refl", "calc_subst", "calc_trans", "check",
          "classes", "coercions", "conjecture", "constants", "context",
          "corollary", "else", "end", "environment", "eval", "example",
          "exists", "exit", "export", "exposing", "extends", "fields", "find_decl",
          "forall", "from", "fun", "have", "help", "hiding", "if",
          "import", "in", "infix", "infixl", "infixr", "instances",
          "let", "local", "match", "namespace", "notation", "obtain", "obtains",
          "omit", "opaque", "open", "options", "parameter", "parameters", "postfix",
          "precedence", "prefix", "premise", "premises", "print", "private", "proof",
          "protected", "qed", "raw", "renaming", "section", "set_option",
          "show", "tactic_hint", "take", "then", "universe",
          "universes", "using", "variable", "variables", "with"].join("|")
    );

    var nameProviders = (
        ["inductive", "structure", "record", "theorem", "axiom",
         "axioms", "lemma", "hypothesis", "definition", "constant"].join("|")
    );

    var storageType = (
        ["Prop", "Type", "Type'", "Type₊", "Type₁", "Type₂", "Type₃"].join("|")
    );

    var storageModifiers = (
        "\\[(" +
            ["abbreviations", "all-transparent", "begin-end-hints", "class", "classes", "coercion",
             "coercions", "declarations", "decls", "instance", "irreducible",
             "multiple-instances", "notation", "notations", "parsing-only", "persistent",
             "reduce-hints", "reducible", "tactic-hints", "visible", "wf", "whnf"
            ].join("|") +
            ")\\]"
    );

    var keywordOperators = (
        [].join("|")
    );

    var keywordMapper = this.$keywords = this.createKeywordMapper({
        "keyword.control" : keywordControls,
        "storage.type" : storageType,
        "keyword.operator" : keywordOperators,
        "variable.language": "sorry",
    }, "identifier");

    var identifierRe = "[A-Za-z_\u03b1-\u03ba\u03bc-\u03fb\u1f00-\u1ffe\u2100-\u214f][A-Za-z0-9_'\u03b1-\u03ba\u03bc-\u03fb\u1f00-\u1ffe\u2070-\u2079\u207f-\u2089\u2090-\u209c\u2100-\u214f]*";
    var operatorRe = new RegExp(["#", "@", "->", "∼", "↔", "/", "==", "=", ":=", "<->",
                                 "/\\", "\\/", "∧", "∨", "≠", "<", ">", "≤", "≥", "¬",
                                 "<=", ">=", "⁻¹", "⬝", "▸", "\\+", "\\*", "-", "/",
                                 "λ", "→", "∃", "∀", ":="].join("|"));
    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used

    this.$rules = {
        "start" : [
            {
                token : "comment", // single line comment "--"
                regex : "--.*$"
            },
            DocCommentHighlightRules.getStartRule("doc-start"),
            {
                token : "comment", // multi line comment "/-"
                regex : "\\/-",
                next : "comment"
            }, {
                stateName: "qqstring",
                token : "string.start", regex : '"', next : [
                    {token : "string.end", regex : '"', next : "start"},
                    {token : "constant.language.escape", regex : /\\[n"\\]/},
                    {defaultToken: "string"}
                ]
            }, {
                token : "keyword.control", regex : nameProviders, next : [
                    {token : "variable.language", regex : identifierRe, next : "start"} ]
            }, {
                token : "constant.numeric", // hex
                regex : "0[xX][0-9a-fA-F]+(L|l|UL|ul|u|U|F|f|ll|LL|ull|ULL)?\\b"
            }, {
                token : "constant.numeric", // float
                regex : "[+-]?\\d+(?:(?:\\.\\d*)?(?:[eE][+-]?\\d+)?)?(L|l|UL|ul|u|U|F|f|ll|LL|ull|ULL)?\\b"
            }, {
                token : "storage.modifier",
                regex : storageModifiers
            }, {
                token : keywordMapper,
                regex : identifierRe
            }, {
                token : "operator",
                regex : operatorRe
            }, {
              token : "punctuation.operator",
              regex : "\\?|\\:|\\,|\\;|\\."
            }, {
                token : "paren.lparen",
                regex : "[[({]"
            }, {
                token : "paren.rparen",
                regex : "[\\])}]"
            }, {
                token : "text",
                regex : "\\s+"
            }
        ],
        "comment" : [ {token: "comment", regex: "-/", next: "start"},
                      {defaultToken: "comment"} ]
    };

    this.embedRules(DocCommentHighlightRules, "doc-",
        [ DocCommentHighlightRules.getEndRule("start") ]);
    this.normalizeRules();
};

oop.inherits(leanHighlightRules, TextHighlightRules);

exports.leanHighlightRules = leanHighlightRules;
});
