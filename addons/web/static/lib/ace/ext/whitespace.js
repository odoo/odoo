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

var lang = require("../lib/lang");

// based on http://www.freehackers.org/Indent_Finder
exports.$detectIndentation = function(lines, fallback) {
    var stats = [];
    var changes = [];
    var tabIndents = 0;
    var prevSpaces = 0;
    var max = Math.min(lines.length, 1000);
    for (var i = 0; i < max; i++) {
        var line = lines[i];
        // ignore empty and comment lines
        if (!/^\s*[^*+\-\s]/.test(line))
            continue;

        if (line[0] == "\t") {
            tabIndents++;
            prevSpaces = -Number.MAX_VALUE;
        } else {
            var spaces = line.match(/^ */)[0].length;
            if (spaces && line[spaces] != "\t") {
                var diff = spaces - prevSpaces;
                if (diff > 0 && !(prevSpaces%diff) && !(spaces%diff))
                    changes[diff] = (changes[diff] || 0) + 1;
    
                stats[spaces] = (stats[spaces] || 0) + 1;
            }
            prevSpaces = spaces;
        }
        // ignore lines ending with backslash
        while (i < max && line[line.length - 1] == "\\")
            line = lines[i++];
    }
    
    function getScore(indent) {
        var score = 0;
        for (var i = indent; i < stats.length; i += indent)
            score += stats[i] || 0;
        return score;
    }

    var changesTotal = changes.reduce(function(a,b){return a+b}, 0);

    var first = {score: 0, length: 0};
    var spaceIndents = 0;
    for (var i = 1; i < 12; i++) {
        var score = getScore(i);
        if (i == 1) {
            spaceIndents = score;
            score = stats[1] ? 0.9 : 0.8;
            if (!stats.length)
                score = 0;
        } else
            score /= spaceIndents;

        if (changes[i])
            score += changes[i] / changesTotal;

        if (score > first.score)
            first = {score: score, length: i};
    }

    if (first.score && first.score > 1.4)
        var tabLength = first.length;

    if (tabIndents > spaceIndents + 1) {
        if (tabLength == 1 || spaceIndents < tabIndents / 4 || first.score < 1.8)
            tabLength = undefined;
        return {ch: "\t", length: tabLength};
    }
    if (spaceIndents > tabIndents + 1)
        return {ch: " ", length: tabLength};
};

exports.detectIndentation = function(session) {
    var lines = session.getLines(0, 1000);
    var indent = exports.$detectIndentation(lines) || {};

    if (indent.ch)
        session.setUseSoftTabs(indent.ch == " ");

    if (indent.length)
        session.setTabSize(indent.length);
    return indent;
};

exports.trimTrailingSpace = function(session, trimEmpty) {
    var doc = session.getDocument();
    var lines = doc.getAllLines();
    
    var min = trimEmpty ? -1 : 0;

    for (var i = 0, l=lines.length; i < l; i++) {
        var line = lines[i];
        var index = line.search(/\s+$/);

        if (index > min)
            doc.removeInLine(i, index, line.length);
    }
};

exports.convertIndentation = function(session, ch, len) {
    var oldCh = session.getTabString()[0];
    var oldLen = session.getTabSize();
    if (!len) len = oldLen;
    if (!ch) ch = oldCh;

    var tab = ch == "\t" ? ch: lang.stringRepeat(ch, len);

    var doc = session.doc;
    var lines = doc.getAllLines();

    var cache = {};
    var spaceCache = {};
    for (var i = 0, l=lines.length; i < l; i++) {
        var line = lines[i];
        var match = line.match(/^\s*/)[0];
        if (match) {
            var w = session.$getStringScreenWidth(match)[0];
            var tabCount = Math.floor(w/oldLen);
            var reminder = w%oldLen;
            var toInsert = cache[tabCount] || (cache[tabCount] = lang.stringRepeat(tab, tabCount));
            toInsert += spaceCache[reminder] || (spaceCache[reminder] = lang.stringRepeat(" ", reminder));

            if (toInsert != match) {
                doc.removeInLine(i, 0, match.length);
                doc.insertInLine({row: i, column: 0}, toInsert);
            }
        }
    }
    session.setTabSize(len);
    session.setUseSoftTabs(ch == " ");
};

exports.$parseStringArg = function(text) {
    var indent = {};
    if (/t/.test(text))
        indent.ch = "\t";
    else if (/s/.test(text))
        indent.ch = " ";
    var m = text.match(/\d+/);
    if (m)
        indent.length = parseInt(m[0], 10);
    return indent;
};

exports.$parseArg = function(arg) {
    if (!arg)
        return {};
    if (typeof arg == "string")
        return exports.$parseStringArg(arg);
    if (typeof arg.text == "string")
        return exports.$parseStringArg(arg.text);
    return arg;
};

exports.commands = [{
    name: "detectIndentation",
    exec: function(editor) {
        exports.detectIndentation(editor.session);
        // todo show message?
    }
}, {
    name: "trimTrailingSpace",
    exec: function(editor) {
        exports.trimTrailingSpace(editor.session);
    }
}, {
    name: "convertIndentation",
    exec: function(editor, arg) {
        var indent = exports.$parseArg(arg);
        exports.convertIndentation(editor.session, indent.ch, indent.length);
    }
}, {
    name: "setIndentation",
    exec: function(editor, arg) {
        var indent = exports.$parseArg(arg);
        indent.length && editor.session.setTabSize(indent.length);
        indent.ch && editor.session.setUseSoftTabs(indent.ch == " ");
    }
}];

});
