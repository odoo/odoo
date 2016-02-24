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

var MockRenderer = exports.MockRenderer = function(visibleRowCount) {
    this.container = document.createElement("div");
    this.scroller = document.createElement("div");
    this.visibleRowCount = visibleRowCount || 20;

    this.layerConfig = {
        firstVisibleRow : 0,
        lastVisibleRow : this.visibleRowCount
    };

    this.isMockRenderer = true;

    this.$gutter = {};
};


MockRenderer.prototype.getFirstVisibleRow = function() {
    return this.layerConfig.firstVisibleRow;
};

MockRenderer.prototype.getLastVisibleRow = function() {
    return this.layerConfig.lastVisibleRow;
};

MockRenderer.prototype.getFirstFullyVisibleRow = function() {
    return this.layerConfig.firstVisibleRow;
};

MockRenderer.prototype.getLastFullyVisibleRow = function() {
    return this.layerConfig.lastVisibleRow;
};

MockRenderer.prototype.getContainerElement = function() {
    return this.container;
};

MockRenderer.prototype.getMouseEventTarget = function() {
    return this.container;
};

MockRenderer.prototype.getTextAreaContainer = function() {
    return this.container;
};

MockRenderer.prototype.addGutterDecoration = function() {
};

MockRenderer.prototype.removeGutterDecoration = function() {
};

MockRenderer.prototype.moveTextAreaToCursor = function() {
};

MockRenderer.prototype.setSession = function(session) {
    this.session = session;
};

MockRenderer.prototype.getSession = function(session) {
    return this.session;
};

MockRenderer.prototype.setTokenizer = function() {
};

MockRenderer.prototype.on = function() {
};

MockRenderer.prototype.updateCursor = function() {
};

MockRenderer.prototype.animateScrolling = function(fromValue, callback) {
    callback && callback();
};

MockRenderer.prototype.scrollToX = function(scrollTop) {};
MockRenderer.prototype.scrollToY = function(scrollLeft) {};

MockRenderer.prototype.scrollToLine = function(line, center) {
    var lineHeight = 16;
    var row = 0;
    for (var l = 1; l < line; l++) {
        row += this.session.getRowLength(l-1);
    }

    if (center) {
        row -= this.visibleRowCount / 2;
    }
    this.scrollToRow(row);
};

MockRenderer.prototype.scrollSelectionIntoView = function() {
};

MockRenderer.prototype.scrollCursorIntoView = function() {
    var cursor = this.session.getSelection().getCursor();
    if (cursor.row < this.layerConfig.firstVisibleRow) {
        this.scrollToRow(cursor.row);
    }
    else if (cursor.row > this.layerConfig.lastVisibleRow) {
        this.scrollToRow(cursor.row);
    }
};

MockRenderer.prototype.scrollToRow = function(row) {
    var row = Math.min(this.session.getLength() - this.visibleRowCount, Math.max(0,
                                                                          row));
    this.layerConfig.firstVisibleRow = row;
    this.layerConfig.lastVisibleRow = row + this.visibleRowCount;
};

MockRenderer.prototype.getScrollTopRow = function() {
  return this.layerConfig.firstVisibleRow;
};

MockRenderer.prototype.draw = function() {
};

MockRenderer.prototype.onChangeTabSize = function(startRow, endRow) {
};

MockRenderer.prototype.updateLines = function(startRow, endRow) {
};

MockRenderer.prototype.updateBackMarkers = function() {
};

MockRenderer.prototype.updateFrontMarkers = function() {
};

MockRenderer.prototype.updateBreakpoints = function() {
};

MockRenderer.prototype.onResize = function() {
};

MockRenderer.prototype.updateFull = function() {
};

MockRenderer.prototype.updateText = function() {
};

MockRenderer.prototype.showCursor = function() {
};

MockRenderer.prototype.visualizeFocus = function() {
};

MockRenderer.prototype.setAnnotations = function() {
};

MockRenderer.prototype.setStyle = function() {
};

MockRenderer.prototype.unsetStyle = function() {
};

MockRenderer.prototype.textToScreenCoordinates = function() {
    return {
        pageX: 0,
        pageY: 0
    }
};

MockRenderer.prototype.screenToTextCoordinates = function() {
    return {
        row: 0,
        column: 0
    }
};

MockRenderer.prototype.adjustWrapLimit = function () {

};

});
