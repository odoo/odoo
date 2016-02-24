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

/*jslint indent: 4, maxerr: 50, white: true, browser: true, vars: true*/
/*global define*/

/**
 * Generates the settings menu
 * @fileOverview Generates the settings menu.
 * @author <a href="mailto:matthewkastor@gmail.com">
 *  Matthew Christopher Kastor-Inare III </a><br />
 *  ☭ Hial Atropa!! ☭
 */

define(function(require, exports, module) {
'use strict';
var egen = require('./element_generator');
var addEditorMenuOptions = require('./add_editor_menu_options').addEditorMenuOptions;
var getSetFunctions = require('./get_set_functions').getSetFunctions;

/**
 * Generates an interactive menu with settings useful to end users.
 * @author <a href="mailto:matthewkastor@gmail.com">
 *  Matthew Christopher Kastor-Inare III </a><br />
 *  ☭ Hial Atropa!! ☭
 * @param {ace.Editor} editor An instance of the ace editor.
 */
module.exports.generateSettingsMenu = function generateSettingsMenu (editor) {
    /**
     * container for dom elements that will go in the menu.
     * @author <a href="mailto:matthewkastor@gmail.com">
     *  Matthew Christopher Kastor-Inare III </a><br />
     *  ☭ Hial Atropa!! ☭
     */
    var elements = [];
    /**
     * Sorts the menu entries (elements var) so they'll appear in alphabetical order
     *  the sort is performed based on the value of the contains property
     *  of each element. Since this is an `array.sort` the array is sorted
     *  in place.
     * @author <a href="mailto:matthewkastor@gmail.com">
     *  Matthew Christopher Kastor-Inare III </a><br />
     *  ☭ Hial Atropa!! ☭
     */
    function cleanupElementsList() {
        elements.sort(function(a, b) {
            var x = a.getAttribute('contains');
            var y = b.getAttribute('contains');
            return x.localeCompare(y);
        });
    }
    /**
     * Wraps all dom elements contained in the elements var with a single
     *  div.
     * @author <a href="mailto:matthewkastor@gmail.com">
     *  Matthew Christopher Kastor-Inare III </a><br />
     *  ☭ Hial Atropa!! ☭
     */
    function wrapElements() {
        var topmenu = document.createElement('div');
        topmenu.setAttribute('id', 'ace_settingsmenu');
        elements.forEach(function(element) {
            topmenu.appendChild(element);
        });
        
        var el = topmenu.appendChild(document.createElement('div'));
        var version = "1.2.0";
        el.style.padding = "1em";
        el.textContent = "Ace version " + version;
        
        return topmenu;
    }
    /**
     * Creates a new menu entry.
     * @author <a href="mailto:matthewkastor@gmail.com">
     *  Matthew Christopher Kastor-Inare III </a><br />
     *  ☭ Hial Atropa!! ☭
     * @param {object} obj This is a reference to the object containing the
     *  set function. It is used to set up event listeners for when the
     *  menu options change.
     * @param {string} clss Maps to the class of the dom element. This is
     *  the name of the object containing the set function e.g. `editor`,
     *  `session`, `renderer`.
     * @param {string} item  This is the set function name. It maps to the
     *  id of the dom element (check, select, input) and to the "contains"
     *  attribute of the div holding both the element and its label.
     * @param {mixed} val This is the value of the setting. It is mapped to
     *  the dom element's value, checked, or selected option accordingly.
     */
    function createNewEntry(obj, clss, item, val) {
        var el;
        var div = document.createElement('div');
        div.setAttribute('contains', item);
        div.setAttribute('class', 'ace_optionsMenuEntry');
        div.setAttribute('style', 'clear: both;');

        div.appendChild(egen.createLabel(
            item.replace(/^set/, '').replace(/([A-Z])/g, ' $1').trim(),
            item
        ));

        if (Array.isArray(val)) {
            el = egen.createSelection(item, val, clss);
            el.addEventListener('change', function(e) {
                try{
                    editor.menuOptions[e.target.id].forEach(function(x) {
                        if(x.textContent !== e.target.textContent) {
                            delete x.selected;
                        }
                    });
                    obj[e.target.id](e.target.value);
                } catch (err) {
                    throw new Error(err);
                }
            });
        } else if(typeof val === 'boolean') {
            el = egen.createCheckbox(item, val, clss);
            el.addEventListener('change', function(e) {
                try{
                    // renderer['setHighlightGutterLine'](true);
                    obj[e.target.id](!!e.target.checked);
                } catch (err) {
                    throw new Error(err);
                }
            });
        } else {
            // this aids in giving the ability to specify settings through
            // post and get requests.
            // /ace_editor.html?setMode=ace/mode/html&setOverwrite=true
            el = egen.createInput(item, val, clss);
            el.addEventListener('change', function(e) {
                try{
                    if(e.target.value === 'true') {
                        obj[e.target.id](true);
                    } else if(e.target.value === 'false') {
                        obj[e.target.id](false);
                    } else {
                        obj[e.target.id](e.target.value);
                    }
                } catch (err) {
                    throw new Error(err);
                }
            });
        }
        el.style.cssText = 'float:right;';
        div.appendChild(el);
        return div;
    }
    /**
     * Generates selection fields for the menu and populates their options
     *  using information from `editor.menuOptions`
     * @author <a href="mailto:matthewkastor@gmail.com">
     *  Matthew Christopher Kastor-Inare III </a><br />
     *  ☭ Hial Atropa!! ☭
     * @param {string} item The set function name.
     * @param {object} esr A reference to the object having the set function.
     * @param {string} clss The name of the object containing the set function.
     * @param {string} fn The matching get function's function name.
     * @returns {DOMElement} Returns a dom element containing a selection
     *  element populated with options. The option whose value matches that
     *  returned from `esr[fn]()` will be selected.
     */
    function makeDropdown(item, esr, clss, fn) {
        var val = editor.menuOptions[item];
        var currentVal = esr[fn]();
        if (typeof currentVal == 'object')
            currentVal = currentVal.$id;
        val.forEach(function(valuex) {
            if (valuex.value === currentVal)
                valuex.selected = 'selected';
        });
        return createNewEntry(esr, clss, item, val);
    }
    /**
     * Processes the set functions returned from `getSetFunctions`. First it
     *  checks for menu options defined in `editor.menuOptions`. If no
     *  options are specified then it checks whether there is a get function
     *  (replace set with get) for the setting. When either of those
     *  conditions are met it will attempt to create a new entry for the
     *  settings menu and push it into the elements array defined above.
     *  It can only do so for get functions which return
     *  strings, numbers, and booleans. A special case is written in for
     *  `getMode` where it looks at the returned objects `$id` property and
     *  forwards that through instead. Other special cases could be written
     *  in but that would get a bit ridiculous.
     * @author <a href="mailto:matthewkastor@gmail.com">
     *  Matthew Christopher Kastor-Inare III </a><br />
     *  ☭ Hial Atropa!! ☭
     * @param {object} setObj An item from the array returned by
     *  `getSetFunctions`.
     */
    function handleSet(setObj) {
        var item = setObj.functionName;
        var esr = setObj.parentObj;
        var clss = setObj.parentName;
        var val;
        var fn = item.replace(/^set/, 'get');
        if(editor.menuOptions[item] !== undefined) {
            // has options for select element
            elements.push(makeDropdown(item, esr, clss, fn));
        } else if(typeof esr[fn] === 'function') {
            // has get function
            try {
                val = esr[fn]();
                if(typeof val === 'object') {
                    // setMode takes a string, getMode returns an object
                    // the $id property of that object is the string
                    // which may be given to setMode...
                    val = val.$id;
                }
                // the rest of the get functions return strings,
                // booleans, or numbers.
                elements.push(
                    createNewEntry(esr, clss, item, val)
                );
            } catch (e) {
                // if there are errors it is because the element
                // does not belong in the settings menu
            }
        }
    }
    addEditorMenuOptions(editor);
    // gather the set functions
    getSetFunctions(editor).forEach(function(setObj) {
        // populate the elements array with good stuff.
        handleSet(setObj);
    });
    // sort the menu entries in the elements list so people can find
    // the settings in alphabetical order.
    cleanupElementsList();
    // dump the entries from the elements list and wrap them up in a div
    return wrapElements();
};

});