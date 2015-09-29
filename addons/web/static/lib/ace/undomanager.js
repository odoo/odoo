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

/**
 * 
 *
 * This object maintains the undo stack for an [[EditSession `EditSession`]].
 * @class UndoManager
 **/

/**
 * 
 * 
 * Resets the current undo state and creates a new `UndoManager`.
 * 
 * @constructor
 **/
var UndoManager = function() {
    this.reset();
};

(function() {

    /**
     * Provides a means for implementing your own undo manager. `options` has one property, `args`, an [[Array `Array`]], with two elements:
     *
     * - `args[0]` is an array of deltas
     * - `args[1]` is the document to associate with
     *
     * @param {Object} options Contains additional properties
     *
     **/
    this.execute = function(options) {
        // Normalize deltas for storage.
        // var deltaSets = this.$serializeDeltas(options.args[0]);
        var deltaSets = options.args[0];
        // Add deltas to undo stack.
        this.$doc  = options.args[1];
        if (options.merge && this.hasUndo()){
            this.dirtyCounter--;
            deltaSets = this.$undoStack.pop().concat(deltaSets);
        }
        this.$undoStack.push(deltaSets);
        
        // Reset redo stack.
        this.$redoStack = [];
        if (this.dirtyCounter < 0) {
            // The user has made a change after undoing past the last clean state.
            // We can never get back to a clean state now until markClean() is called.
            this.dirtyCounter = NaN;
        }
        this.dirtyCounter++;
    };

    /**
     * [Perform an undo operation on the document, reverting the last change.]{: #UndoManager.undo}
     * @param {Boolean} dontSelect {:dontSelect}
     *
     * 
     * @returns {Range} The range of the undo.
     **/
    this.undo = function(dontSelect) {
        var deltaSets = this.$undoStack.pop();
        var undoSelectionRange = null;
        if (deltaSets) {
            undoSelectionRange = this.$doc.undoChanges(this.$deserializeDeltas(deltaSets), dontSelect);
            this.$redoStack.push(deltaSets);
            this.dirtyCounter--;
        }

        return undoSelectionRange;
    };

    /**
     * [Perform a redo operation on the document, reimplementing the last change.]{: #UndoManager.redo}
     * @param {Boolean} dontSelect {:dontSelect}
     *
     * 
     **/
    this.redo = function(dontSelect) {
        var deltaSets = this.$redoStack.pop();
        var redoSelectionRange = null;
        if (deltaSets) {
            redoSelectionRange =
                this.$doc.redoChanges(this.$deserializeDeltas(deltaSets), dontSelect);
            this.$undoStack.push(deltaSets);
            this.dirtyCounter++;
        }
        return redoSelectionRange;
    };

    /**
     * 
     * Destroys the stack of undo and redo redo operations.
     **/
    this.reset = function() {
        this.$undoStack = [];
        this.$redoStack = [];
        this.dirtyCounter = 0;
    };

    /**
     * 
     * Returns `true` if there are undo operations left to perform.
     * @returns {Boolean}
     **/
    this.hasUndo = function() {
        return this.$undoStack.length > 0;
    };

    /**
     * 
     * Returns `true` if there are redo operations left to perform.
     * @returns {Boolean}
     **/
    this.hasRedo = function() {
        return this.$redoStack.length > 0;
    };

    /**
     *
     * Marks the current status clean
     **/
    this.markClean = function() {
        this.dirtyCounter = 0;
    };

    /**
     *
     * Returns if the current status is clean
     * @returns {Boolean}
     **/
    this.isClean = function() {
        return this.dirtyCounter === 0;
    };
    
    // Serializes deltaSets to reduce memory usage.
    this.$serializeDeltas = function(deltaSets) {
        return cloneDeltaSetsObj(deltaSets, $serializeDelta);
    };
    
    // Deserializes deltaSets to allow application to the document.
    this.$deserializeDeltas = function(deltaSets) {
        return cloneDeltaSetsObj(deltaSets, $deserializeDelta);
    };
    
    function $serializeDelta(delta){
        return {
            action: delta.action,
            start: delta.start,
            end: delta.end,
            lines: delta.lines.length == 1 ? null : delta.lines,
            text: delta.lines.length == 1 ? delta.lines[0] : null,
        };
    }
        
    function $deserializeDelta(delta) {
        return {
            action: delta.action,
            start: delta.start,
            end: delta.end,
            lines: delta.lines || [delta.text]
        };
    }
    
    function cloneDeltaSetsObj(deltaSets_old, fnGetModifiedDelta) {
        var deltaSets_new = new Array(deltaSets_old.length);
        for (var i = 0; i < deltaSets_old.length; i++) {
            var deltaSet_old = deltaSets_old[i];
            var deltaSet_new = { group: deltaSet_old.group, deltas: new Array(deltaSet_old.length)};
            
            for (var j = 0; j < deltaSet_old.deltas.length; j++) {
                var delta_old = deltaSet_old.deltas[j];
                deltaSet_new.deltas[j] = fnGetModifiedDelta(delta_old);
            }
            
            deltaSets_new[i] = deltaSet_new;
        }
        return deltaSets_new;
    }
    
}).call(UndoManager.prototype);

exports.UndoManager = UndoManager;
});
