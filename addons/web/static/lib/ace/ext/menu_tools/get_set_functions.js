/* ***** BEGIN LICENSE BLOCK *****
 * Distributed under the BSD license:
 *
 * Copyright (c) 2013 Matthew Christopher Kastor-Inare III, Atropa Inc. Intl
 * All rights reserved.
 *
 * Contributed to Ajax.org under the BSD license.
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

/*jslint indent: 4, maxerr: 50, white: true, browser: true, vars: true */
/*global define*/

/**
 * Get Set Functions
 * @fileOverview Get Set Functions <br />
 * Gets various functions for setting settings.
 * @author <a href="mailto:matthewkastor@gmail.com">
 *  Matthew Christopher Kastor-Inare III </a><br />
 *  ☭ Hial Atropa!! ☭
 */

define(function(require, exports, module) {
'use strict';
/**
 * Generates a list of set functions for the settings menu.
 * @author <a href="mailto:matthewkastor@gmail.com">
 *  Matthew Christopher Kastor-Inare III </a><br />
 *  ☭ Hial Atropa!! ☭
 * @param {object} editor The editor instance
 * @return {array} Returns an array of objects. Each object contains the
 *  following properties: functionName, parentObj, and parentName. The
 *  function name will be the name of a method beginning with the string
 *  `set` which was found. The parent object will be a reference to the
 *  object having the method matching the function name. The parent name
 *  will be a string representing the identifier of the parent object e.g.
 *  `editor`, `session`, or `renderer`.
 */
module.exports.getSetFunctions = function getSetFunctions (editor) {
    /**
     * Output array. Will hold the objects described above.
     * @author <a href="mailto:matthewkastor@gmail.com">
     *  Matthew Christopher Kastor-Inare III </a><br />
     *  ☭ Hial Atropa!! ☭
     */
    var out = [];
    /**
     * This object provides a map between the objects which will be
     *  traversed and the parent name which will appear in the output.
     * @author <a href="mailto:matthewkastor@gmail.com">
     *  Matthew Christopher Kastor-Inare III </a><br />
     *  ☭ Hial Atropa!! ☭
     */
    var my = {
        'editor' : editor,
        'session' : editor.session,
        'renderer' : editor.renderer
    };
    /**
     * This array will hold the set function names which have already been
     *  found so that they are not added to the output multiple times.
     * @author <a href="mailto:matthewkastor@gmail.com">
     *  Matthew Christopher Kastor-Inare III </a><br />
     *  ☭ Hial Atropa!! ☭
     */
    var opts = [];
    /**
     * This is a list of set functions which will not appear in the settings
     *  menu. I don't know what to do with setKeyboardHandler. When I tried
     *  to use it, it didn't appear to be working. Someone who knows better
     *  could remove it from this list and add it's options to
     *  add_editor_menu_options.js
     * @author <a href="mailto:matthewkastor@gmail.com">
     *  Matthew Christopher Kastor-Inare III </a><br />
     *  ☭ Hial Atropa!! ☭
     */
    var skip = [
        'setOption',
        'setUndoManager',
        'setDocument',
        'setValue',
        'setBreakpoints',
        'setScrollTop',
        'setScrollLeft',
        'setSelectionStyle',
        'setWrapLimitRange'
    ];


    /**
     * This will search the objects mapped to the `my` variable above. When
     *  it finds a set function in the object that is not listed in the
     *  `skip` list or the `opts` list it will push a new object to the
     *  output array.
     * @author <a href="mailto:matthewkastor@gmail.com">
     *  Matthew Christopher Kastor-Inare III </a><br />
     *  ☭ Hial Atropa!! ☭
     */
    ['renderer', 'session', 'editor'].forEach(function(esra) {
        var esr = my[esra];
        var clss = esra;
        for(var fn in esr) {
            if(skip.indexOf(fn) === -1) {
                if(/^set/.test(fn) && opts.indexOf(fn) === -1) {
                    // found set function
                    opts.push(fn);
                    out.push({
                        'functionName' : fn,
                        'parentObj' : esr,
                        'parentName' : clss
                    });
                }
            }
        }
    });
    return out;
};

});