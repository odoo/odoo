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

var oop = require("./lib/oop");
var lang = require("./lib/lang");
var EventEmitter = require("./lib/event_emitter").EventEmitter;

var Editor = require("./editor").Editor;
var Renderer = require("./virtual_renderer").VirtualRenderer;
var EditSession = require("./edit_session").EditSession;

/** 
 * @class Split
 *
 *
 *
 **/


var Split = function(container, theme, splits) {
    this.BELOW = 1;
    this.BESIDE = 0;

    this.$container = container;
    this.$theme = theme;
    this.$splits = 0;
    this.$editorCSS = "";
    this.$editors = [];
    this.$orientation = this.BESIDE;

    this.setSplits(splits || 1);
    this.$cEditor = this.$editors[0];


    this.on("focus", function(editor) {
        this.$cEditor = editor;
    }.bind(this));
};

(function(){

    oop.implement(this, EventEmitter);

    this.$createEditor = function() {
        var el = document.createElement("div");
        el.className = this.$editorCSS;
        el.style.cssText = "position: absolute; top:0px; bottom:0px";
        this.$container.appendChild(el);
        var editor = new Editor(new Renderer(el, this.$theme));

        editor.on("focus", function() {
            this._emit("focus", editor);
        }.bind(this));

        this.$editors.push(editor);
        editor.setFontSize(this.$fontSize);
        return editor;
    };

    this.setSplits = function(splits) {
        var editor;
        if (splits < 1) {
            throw "The number of splits have to be > 0!";
        }

        if (splits == this.$splits) {
            return;
        } else if (splits > this.$splits) {
            while (this.$splits < this.$editors.length && this.$splits < splits) {
                editor = this.$editors[this.$splits];
                this.$container.appendChild(editor.container);
                editor.setFontSize(this.$fontSize);
                this.$splits ++;
            }
            while (this.$splits < splits) {
                this.$createEditor();
                this.$splits ++;
            }
        } else {
            while (this.$splits > splits) {
                editor = this.$editors[this.$splits - 1];
                this.$container.removeChild(editor.container);
                this.$splits --;
            }
        }
        this.resize();
    };

    /**
     * 
     * Returns the number of splits.
     * @returns {Number}
     **/
    this.getSplits = function() {
        return this.$splits;
    };

    /**
     * @param {Number} idx The index of the editor you want
     *
     * Returns the editor identified by the index `idx`.
     *
     **/
    this.getEditor = function(idx) {
        return this.$editors[idx];
    };

    /**
     * 
     * Returns the current editor.
     * @returns {Editor}
     **/
    this.getCurrentEditor = function() {
        return this.$cEditor;
    };

    /** 
     * Focuses the current editor.
     * @related Editor.focus
     **/
    this.focus = function() {
        this.$cEditor.focus();
    };

    /** 
     * Blurs the current editor.
     * @related Editor.blur
     **/
    this.blur = function() {
        this.$cEditor.blur();
    };

    /** 
     * 
     * @param {String} theme The name of the theme to set
     * 
     * Sets a theme for each of the available editors.
     * @related Editor.setTheme
     **/
    this.setTheme = function(theme) {
        this.$editors.forEach(function(editor) {
            editor.setTheme(theme);
        });
    };

    /** 
     * 
     * @param {String} keybinding 
     * 
     * Sets the keyboard handler for the editor.
     * @related editor.setKeyboardHandler
     **/
    this.setKeyboardHandler = function(keybinding) {
        this.$editors.forEach(function(editor) {
            editor.setKeyboardHandler(keybinding);
        });
    };

    /** 
     * 
     * @param {Function} callback A callback function to execute
     * @param {String} scope The default scope for the callback
     * 
     * Executes `callback` on all of the available editors. 
     *
     **/
    this.forEach = function(callback, scope) {
        this.$editors.forEach(callback, scope);
    };


    this.$fontSize = "";
    /** 
     * @param {Number} size The new font size
     * 
     * Sets the font size, in pixels, for all the available editors.
     *
     **/
    this.setFontSize = function(size) {
        this.$fontSize = size;
        this.forEach(function(editor) {
           editor.setFontSize(size);
        });
    };

    this.$cloneSession = function(session) {
        var s = new EditSession(session.getDocument(), session.getMode());

        var undoManager = session.getUndoManager();
        if (undoManager) {
            var undoManagerProxy = new UndoManagerProxy(undoManager, s);
            s.setUndoManager(undoManagerProxy);
        }

        // Overwrite the default $informUndoManager function such that new delas
        // aren't added to the undo manager from the new and the old session.
        s.$informUndoManager = lang.delayedCall(function() { s.$deltas = []; });

        // Copy over 'settings' from the session.
        s.setTabSize(session.getTabSize());
        s.setUseSoftTabs(session.getUseSoftTabs());
        s.setOverwrite(session.getOverwrite());
        s.setBreakpoints(session.getBreakpoints());
        s.setUseWrapMode(session.getUseWrapMode());
        s.setUseWorker(session.getUseWorker());
        s.setWrapLimitRange(session.$wrapLimitRange.min,
                            session.$wrapLimitRange.max);
        s.$foldData = session.$cloneFoldData();

        return s;
    };

   /** 
     * 
     * @param {EditSession} session The new edit session
     * @param {Number} idx The editor's index you're interested in
     * 
     * Sets a new [[EditSession `EditSession`]] for the indicated editor.
     * @related Editor.setSession
     **/
    this.setSession = function(session, idx) {
        var editor;
        if (idx == null) {
            editor = this.$cEditor;
        } else {
            editor = this.$editors[idx];
        }

        // Check if the session is used already by any of the editors in the
        // split. If it is, we have to clone the session as two editors using
        // the same session can cause terrible side effects (e.g. UndoQueue goes
        // wrong). This also gives the user of Split the possibility to treat
        // each session on each split editor different.
        var isUsed = this.$editors.some(function(editor) {
           return editor.session === session;
        });

        if (isUsed) {
            session = this.$cloneSession(session);
        }
        editor.setSession(session);

        // Return the session set on the editor. This might be a cloned one.
        return session;
    };

   /** 
     * 
     * Returns the orientation.
     * @returns {Number}
     **/
    this.getOrientation = function() {
        return this.$orientation;
    };

   /** 
     * 
     * Sets the orientation.
     * @param {Number} orientation The new orientation value
     *
     *
     **/
    this.setOrientation = function(orientation) {
        if (this.$orientation == orientation) {
            return;
        }
        this.$orientation = orientation;
        this.resize();
    };

   /**  
     * Resizes the editor.
     **/
    this.resize = function() {
        var width = this.$container.clientWidth;
        var height = this.$container.clientHeight;
        var editor;

        if (this.$orientation == this.BESIDE) {
            var editorWidth = width / this.$splits;
            for (var i = 0; i < this.$splits; i++) {
                editor = this.$editors[i];
                editor.container.style.width = editorWidth + "px";
                editor.container.style.top = "0px";
                editor.container.style.left = i * editorWidth + "px";
                editor.container.style.height = height + "px";
                editor.resize();
            }
        } else {
            var editorHeight = height / this.$splits;
            for (var i = 0; i < this.$splits; i++) {
                editor = this.$editors[i];
                editor.container.style.width = width + "px";
                editor.container.style.top = i * editorHeight + "px";
                editor.container.style.left = "0px";
                editor.container.style.height = editorHeight + "px";
                editor.resize();
            }
        }
    };

}).call(Split.prototype);

 
function UndoManagerProxy(undoManager, session) {
    this.$u = undoManager;
    this.$doc = session;
}

(function() {
    this.execute = function(options) {
        this.$u.execute(options);
    };

    this.undo = function() {
        var selectionRange = this.$u.undo(true);
        if (selectionRange) {
            this.$doc.selection.setSelectionRange(selectionRange);
        }
    };

    this.redo = function() {
        var selectionRange = this.$u.redo(true);
        if (selectionRange) {
            this.$doc.selection.setSelectionRange(selectionRange);
        }
    };

    this.reset = function() {
        this.$u.reset();
    };

    this.hasUndo = function() {
        return this.$u.hasUndo();
    };

    this.hasRedo = function() {
        return this.$u.hasRedo();
    };
}).call(UndoManagerProxy.prototype);

exports.Split = Split;
});
