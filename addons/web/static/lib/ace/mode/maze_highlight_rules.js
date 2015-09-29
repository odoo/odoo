/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2012, Ajax.org B.V.
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
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var MazeHighlightRules = function() {
    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used

    this.$rules = {
        start: [{
            token: "keyword.control",
            regex: /##|``/,
            comment: "Wall"
        }, {
            token: "entity.name.tag",
            regex: /\.\./,
            comment: "Path"
        }, {
            token: "keyword.control",
            regex: /<>/,
            comment: "Splitter"
        }, {
            token: "entity.name.tag",
            regex: /\*[\*A-Za-z0-9]/,
            comment: "Signal"
        }, {
            token: "constant.numeric",
            regex: /[0-9]{2}/,
            comment: "Pause"
        }, {
            token: "keyword.control",
            regex: /\^\^/,
            comment: "Start"
        }, {
            token: "keyword.control",
            regex: /\(\)/,
            comment: "Hole"
        }, {
            token: "support.function",
            regex: />>/,
            comment: "Out"
        }, {
            token: "support.function",
            regex: />\//,
            comment: "Ln Out"
        }, {
            token: "support.function",
            regex: /<</,
            comment: "In"
        }, {
            token: "keyword.control",
            regex: /--/,
            comment: "One use"
        }, {
            token: "constant.language",
            regex: /%[LRUDNlrudn]/,
            comment: "Direction"
        }, {
            token: [
                "entity.name.function",
                "keyword.other",
                "keyword.operator",
                "keyword.other",
                "keyword.operator",
                "constant.numeric",
                "keyword.operator",
                "keyword.other",
                "keyword.operator",
                "constant.numeric",
                "string.quoted.double",
                "string.quoted.single"
            ],
            regex: /([A-Za-z][A-Za-z0-9])( *-> *)(?:([-+*\/]=)( *)((?:-)?)([0-9]+)|(=)( *)(?:((?:-)?)([0-9]+)|("[^"]*")|('[^']*')))/,
            comment: "Assignment function"
        }, {
            token: [
                "entity.name.function",
                "keyword.other",
                "keyword.control",
                "keyword.other",
                "keyword.operator",
                "keyword.other",
                "keyword.operator",
                "constant.numeric",
                "entity.name.tag",
                "keyword.other",
                "keyword.control",
                "keyword.other",
                "constant.language",
                "keyword.other",
                "keyword.control",
                "keyword.other",
                "constant.language"
            ],
            regex: /([A-Za-z][A-Za-z0-9])( *-> *)(IF|if)( *)(?:([<>]=?|==)( *)((?:-)?)([0-9]+)|(\*[\*A-Za-z0-9]))( *)(THEN|then)( *)(%[LRUDNlrudn])(?:( *)(ELSE|else)( *)(%[LRUDNlrudn]))?/,
            comment: "Equality Function"
        }, {
            token: "entity.name.function",
            regex: /[A-Za-z][A-Za-z0-9]/,
            comment: "Function cell"
        }, {
            token: "comment.line.double-slash",
            regex: / *\/\/.*/,
            comment: "Comment"
        }]
    };

    this.normalizeRules();
};

MazeHighlightRules.metaData = {
    fileTypes: ["mz"],
    name: "Maze",
    scopeName: "source.maze"
};


oop.inherits(MazeHighlightRules, TextHighlightRules);

exports.MazeHighlightRules = MazeHighlightRules;
});
