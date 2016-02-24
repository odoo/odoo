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
var TokenIterator = require("ace/token_iterator").TokenIterator;
exports.newLines = [{
    type: 'support.php_tag',
    value: '<?php'
}, {
    type: 'support.php_tag',
    value: '<?'
}, {
    type: 'support.php_tag',
    value: '?>'
}, {
    type: 'paren.lparen',
    value: '{',
    indent: true
}, {
    type: 'paren.rparen',
    breakBefore: true,
    value: '}',
    indent: false
}, {
    type: 'paren.rparen',
    breakBefore: true,
    value: '})',
    indent: false,
    dontBreak: true
}, {
    type: 'comment'
}, {
    type: 'text',
    value: ';'
}, {
    type: 'text',
    value: ':',
    context: 'php'
}, {
    type: 'keyword',
    value: 'case',
    indent: true,
    dontBreak: true
}, {
    type: 'keyword',
    value: 'default',
    indent: true,
    dontBreak: true
}, {
    type: 'keyword',
    value: 'break',
    indent: false,
    dontBreak: true
}, {
    type: 'punctuation.doctype.end',
    value: '>'
}, {
    type: 'meta.tag.punctuation.end',
    value: '>'
}, {
    type: 'meta.tag.punctuation.begin',
    value: '<',
    blockTag: true,
    indent: true,
    dontBreak: true
}, {
    type: 'meta.tag.punctuation.begin',
    value: '</',
    indent: false,
    breakBefore: true,
    dontBreak: true
}, {
    type: 'punctuation.operator',
    value: ';'
}];

exports.spaces = [{
    type: 'xml-pe',
    prepend: true
},{
    type: 'entity.other.attribute-name',
    prepend: true
}, {
    type: 'storage.type',
    value: 'var',
    append: true
}, {
    type: 'storage.type',
    value: 'function',
    append: true
}, {
    type: 'keyword.operator',
    value: '='
}, {
    type: 'keyword',
    value: 'as',
    prepend: true,
    append: true
}, {
    type: 'keyword',
    value: 'function',
    append: true
}, {
    type: 'support.function',
    next: /[^\(]/,
    append: true
}, {
    type: 'keyword',
    value: 'or',
    append: true,
    prepend: true
}, {
    type: 'keyword',
    value: 'and',
    append: true,
    prepend: true
}, {
    type: 'keyword',
    value: 'case',
    append: true
}, {
    type: 'keyword.operator',
    value: '||',
    append: true,
    prepend: true
}, {
    type: 'keyword.operator',
    value: '&&',
    append: true,
    prepend: true
}];
exports.singleTags = ['!doctype','area','base','br','hr','input','img','link','meta'];

exports.transform = function(iterator, maxPos, context) {
    var token = iterator.getCurrentToken();
    
    var newLines = exports.newLines;
    var spaces = exports.spaces;
    var singleTags = exports.singleTags;

    var code = '';
    
    var indentation = 0;
    var dontBreak = false;
    var tag;
    var lastTag;
    var lastToken = {};
    var nextTag;
    var nextToken = {};
    var breakAdded = false;
    var value = '';

    while (token!==null) {
        console.log(token);

        if( !token ){
            token = iterator.stepForward();
            continue;
        }

        //change syntax
        //php
        if( token.type == 'support.php_tag' && token.value != '?>' ){
            context = 'php';
        }
        else if( token.type == 'support.php_tag' && token.value == '?>' ){
            context = 'html';
        }
        //css
        else if( token.type == 'meta.tag.name.style' && context != 'css' ){
            context = 'css';
        }
        else if( token.type == 'meta.tag.name.style' && context == 'css' ){
            context = 'html';
        }
        //js
        else if( token.type == 'meta.tag.name.script' && context != 'js' ){
            context = 'js';
        }
        else if( token.type == 'meta.tag.name.script' && context == 'js' ){
            context = 'html';
        }

        nextToken = iterator.stepForward();

        //tag name
        if (nextToken && nextToken.type.indexOf('meta.tag.name') == 0) {
            nextTag = nextToken.value;
        }

        //don't linebreak
        if ( lastToken.type == 'support.php_tag' && lastToken.value == '<?=') {
            dontBreak = true;
        }

        //lowercase
        if (token.type == 'meta.tag.name') {
            token.value = token.value.toLowerCase();
        }

        //trim spaces
        if (token.type == 'text') {
            token.value = token.value.trim();
        }

        //skip empty tokens
        if (!token.value) {
            token = nextToken;
            continue;
        }

        //put spaces back in
        value = token.value;
        for (var i in spaces) {
            if (
                token.type == spaces[i].type &&
                (!spaces[i].value || token.value == spaces[i].value) &&
                (
                    nextToken &&
                    (!spaces[i].next || spaces[i].next.test(nextToken.value))
                )
            ) {
                if (spaces[i].prepend) {
                    value = ' ' + token.value;
                }

                if (spaces[i].append) {
                    value += ' ';
                }
            }
        }

        //tag name
        if (token.type.indexOf('meta.tag.name') == 0) {
            tag = token.value;
            //console.log(tag);
        }

        //new line before
        breakAdded = false;

        //outdent
        for (i in newLines) {
            if (
                token.type == newLines[i].type &&
                (
                    !newLines[i].value ||
                    token.value == newLines[i].value
                ) &&
                (
                    !newLines[i].blockTag ||
                    singleTags.indexOf(nextTag) === -1
                ) &&
                (
                    !newLines[i].context ||
                    newLines[i].context === context
                )
            ) {
                if (newLines[i].indent === false) {
                    indentation--;
                }

                if (
                    newLines[i].breakBefore &&
                    ( !newLines[i].prev || newLines[i].prev.test(lastToken.value) )
                ) {
                    code += "\n";
                    breakAdded = true;

                    //indent
                    for (i = 0; i < indentation; i++) {
                        code += "\t";
                    }
                }

                break;
            }
        }

        if (dontBreak===false) {
            for (i in newLines) {
                if (
                    lastToken.type == newLines[i].type &&
                    (
                        !newLines[i].value || lastToken.value == newLines[i].value
                    ) &&
                    (
                        !newLines[i].blockTag ||
                        singleTags.indexOf(tag) === -1
                    ) &&
                    (
                        !newLines[i].context ||
                        newLines[i].context === context
                    )
                ) {
                    if (newLines[i].indent === true) {
                        indentation++;
                    }

                    if (!newLines[i].dontBreak  && !breakAdded) {
                        code += "\n";

                        //indent
                        for (i = 0; i < indentation; i++) {
                            code += "\t";
                        }
                    }

                    break;
                }
            }
        }

        code += value;

        //linebreaks back on after end short php tag
        if ( lastToken.type == 'support.php_tag' && lastToken.value == '?>' ) {
            dontBreak = false;
        }

        //next token
        lastTag = tag;

        lastToken = token;

        token = nextToken;

        if (token===null) {
            break;
        }
    }
    
    return code;
};



});