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

var HashHandler = require("./hash_handler").HashHandler;
exports.handler = new HashHandler();

[{
    bindKey: "Shift-Tab|Tab",
    command: "passKeysToBrowser"
}, {
    bindKey: {win: "Ctrl-L", mac: "Cmd-L"},
    command: "passKeysToBrowser"
}, {
    bindKey: {win: "Ctrl-G", mac: "Cmd-G"},
    command: "gotoline"
}, {
    bindKey: {win: "Ctrl-T|Ctrl-Shift-T", mac: "Cmd-T|Cmd-Shift-T"},
    command: "passKeysToBrowser"
}, {
    bindKey: {win: "Ctrl-G", mac: "Cmd-G"},
    command: "passKeysToBrowser"
}, {
    bindKey: {win: "Ctrl-G", mac: "Cmd-G"},
    command: "passKeysToBrowser"
}, {
    name: "golineup",
    bindKey: {win: null, mac: "Ctrl-P"},
}, {
    name: "golinedown",
    bindKey: {win: null, mac: "Ctrl-N"},
}, {
    name: "gotoleft",    
    bindKey: {win: null, mac: "Ctrl-B"},
}, {
    name: "gotoright",
    bindKey: {win: null, mac: "Ctrl-F"},
}, {
    name: "gotolineend",
    bindKey: {win: null, mac: "Ctrl-E"},
}, {
    name: "gotolinestart",
    bindKey: {win: null, mac: "Ctrl-A"},
}
].forEach(function(k) {
    var bindKey = k.bindKey;
    if (typeof bindKey == "object")
        bindKey = bindKey[exports.handler.platform];
    exports.handler.bindKey(bindKey, k.command);
});
exports.handler.$id = "ace/keyboard/textarea";

});
