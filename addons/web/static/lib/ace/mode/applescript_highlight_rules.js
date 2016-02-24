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

var AppleScriptHighlightRules = function() {
    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used
    var keywords = (
        "about|above|after|against|and|around|as|at|back|before|beginning|" +
        "behind|below|beneath|beside|between|but|by|considering|" +
        "contain|contains|continue|copy|div|does|eighth|else|end|equal|" +
        "equals|error|every|exit|fifth|first|for|fourth|from|front|" +
        "get|given|global|if|ignoring|in|into|is|it|its|last|local|me|" +
        "middle|mod|my|ninth|not|of|on|onto|or|over|prop|property|put|ref|" +
        "reference|repeat|returning|script|second|set|seventh|since|" +
        "sixth|some|tell|tenth|that|the|then|third|through|thru|" +
        "timeout|times|to|transaction|try|until|where|while|whose|with|without"
    );

    var builtinConstants = (
        "AppleScript|false|linefeed|return|pi|quote|result|space|tab|true"
    );

    var builtinFunctions = (
        "activate|beep|count|delay|launch|log|offset|read|round|run|say|" +
        "summarize|write"
    );

    var builtinTypes = (
        "alias|application|boolean|class|constant|date|file|integer|list|" +
        "number|real|record|string|text|character|characters|contents|day|" +
        "frontmost|id|item|length|month|name|paragraph|paragraphs|rest|" +
        "reverse|running|time|version|weekday|word|words|year"
    );

    var keywordMapper = this.createKeywordMapper({
        "support.function": builtinFunctions,
        "constant.language": builtinConstants,
        "support.type": builtinTypes,
        "keyword": keywords
    }, "identifier");

    this.$rules = {
        "start": [
            {
                token: "comment",
                regex: "--.*$"
            },
            {
                token : "comment", // multi line comment
                regex : "\\(\\*",
                next : "comment"
            },
            {
                token: "string",           // " string
                regex: '".*?"'
            },
            {
                token: "support.type",
                regex: '\\b(POSIX file|POSIX path|(date|time) string|quoted form)\\b'
            },
            {
                token: "support.function",
                regex: '\\b(clipboard info|the clipboard|info for|list (disks|folder)|' +
          'mount volume|path to|(close|open for) access|(get|set) eof|' +
          'current date|do shell script|get volume settings|random number|' +
          'set volume|system attribute|system info|time to GMT|' +
          '(load|run|store) script|scripting components|' +
          'ASCII (character|number)|localized string|' +
          'choose (application|color|file|file name|' +
          'folder|from list|remote application|URL)|' +
          'display (alert|dialog))\\b|^\\s*return\\b'
            },
            {
                token: "constant.language",
                regex: '\\b(text item delimiters|current application|missing value)\\b'
            },
            {
                token: "keyword",
                regex: '\\b(apart from|aside from|instead of|out of|greater than|' +
          "isn't|(doesn't|does not) (equal|come before|come after|contain)|" +
          '(greater|less) than( or equal)?|(starts?|ends|begins?) with|' +
          'contained by|comes (before|after)|a (ref|reference))\\b'
            },
            {
                token: keywordMapper,
                regex: "[a-zA-Z][a-zA-Z0-9_]*\\b"
            }
        ],
        "comment": [
            {
                token: "comment", // closing comment
                regex: "\\*\\)",
                next: "start"
            }, {
                defaultToken: "comment"
            }
        ]
    }

    this.normalizeRules();
};

oop.inherits(AppleScriptHighlightRules, TextHighlightRules);

exports.AppleScriptHighlightRules = AppleScriptHighlightRules;
});
