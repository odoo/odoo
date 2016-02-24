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
var lang = require("../lib/lang");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

function safeCreateRegexp(source, flag) {
    try {
        return new RegExp(source, flag);
    } catch(e) {}
}

var C9SearchHighlightRules = function() {

    // regexp must not have capturing parentheses. Use (?:) instead.
    // regexps are ordered -> the first match is used
    this.$rules = {
        "start" : [
            {
                tokenNames : ["c9searchresults.constant.numeric", "c9searchresults.text", "c9searchresults.text", "c9searchresults.keyword"],
                regex : "(^\\s+[0-9]+)(:\\s)(.+)",
                onMatch : function(val, state, stack) {
                    var values = this.splitRegex.exec(val);
                    var types = this.tokenNames;
                    var tokens = [{
                        type: types[0],
                        value: values[1]
                    },{
                        type: types[1],
                        value: values[2]
                    }];
                    
                    var regex = stack[1];
                    var str = values[3];
                    
                    var m;
                    var last = 0;
                    if (regex && regex.exec) {
                        regex.lastIndex = 0;
                        while (m = regex.exec(str)) {
                            var skipped = str.substring(last, m.index);
                            last = regex.lastIndex;
                            if (skipped)
                                tokens.push({type: types[2], value: skipped});
                            if (m[0])
                                tokens.push({type: types[3], value: m[0]});
                            else if (!skipped)
                                break;
                        }
                    }
                    if (last < str.length)
                        tokens.push({type: types[2], value: str.substr(last)});
                    return tokens;
                }
            },
            {
                token : ["string", "text"], // single line
                regex : "(\\S.*)(:$)"
            },
            {
                regex : "Searching for .*$",
                onMatch: function(val, state, stack) {
                    var parts = val.split("\x01");
                    if (parts.length < 3)
                        return "text";

                    var options, search, replace;
                    
                    var i = 0;
                    var tokens = [{
                        value: parts[i++] + "'",
                        type: "text"
                    }, {
                        value: search = parts[i++],
                        type: "text" // "c9searchresults.keyword"
                    }, {
                        value: "'" + parts[i++],
                        type: "text"
                    }];
                    
                    // replaced
                    if (parts[2] !== " in") {
                        replace = parts[i];
                        tokens.push({
                            value: "'" + parts[i++] + "'",
                            type: "text"
                        }, {
                            value: parts[i++],
                            type: "text"
                        });
                    }
                    // path
                    tokens.push({
                        value: " " + parts[i++] + " ",
                        type: "text"
                    });
                    // options
                    if (parts[i+1]) {
                        options = parts[i+1];
                        tokens.push({
                            value: "(" + parts[i+1] + ")",
                            type: "text"
                        });
                        i += 1;
                    } else {
                        i -= 1;
                    }
                    while (i++ < parts.length) {
                        parts[i] && tokens.push({
                            value: parts[i],
                            type: "text"
                        });
                    }
                    
                    if (replace) {
                        search = replace;
                        options = "";
                    }
                    
                    if (search) {
                        if (!/regex/.test(options))
                            search = lang.escapeRegExp(search);
                        if (/whole/.test(options))
                            search = "\\b" + search + "\\b";
                    }
                    
                    var regex = search && safeCreateRegexp(
                        "(" + search + ")",
                        / sensitive/.test(options) ? "g" : "ig"
                    );
                    if (regex) {
                        stack[0] = state;
                        stack[1] = regex;
                    }
                    
                    return tokens;
                }
            },
            {
                regex : "\\d+",
                token: "constant.numeric"
            }
        ]
    };
};

oop.inherits(C9SearchHighlightRules, TextHighlightRules);

exports.C9SearchHighlightRules = C9SearchHighlightRules;

});