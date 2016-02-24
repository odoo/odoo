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
var dom = require("./lib/dom");
var event = require("./lib/event");
var EventEmitter = require("./lib/event_emitter").EventEmitter;

/**
 * An abstract class representing a native scrollbar control.
 * @class ScrollBar
 **/

/**
 * Creates a new `ScrollBar`. `parent` is the owner of the scroll bar.
 * @param {DOMElement} parent A DOM element 
 *
 * @constructor
 **/
var ScrollBar = function(parent) {
    this.element = dom.createElement("div");
    this.element.className = "ace_scrollbar ace_scrollbar" + this.classSuffix;

    this.inner = dom.createElement("div");
    this.inner.className = "ace_scrollbar-inner";
    this.element.appendChild(this.inner);

    parent.appendChild(this.element);

    this.setVisible(false);
    this.skipEvent = false;

    event.addListener(this.element, "scroll", this.onScroll.bind(this));
    event.addListener(this.element, "mousedown", event.preventDefault);
};

(function() {
    oop.implement(this, EventEmitter);

    this.setVisible = function(isVisible) {
        this.element.style.display = isVisible ? "" : "none";
        this.isVisible = isVisible;
    };
}).call(ScrollBar.prototype);

/**
 * Represents a vertical scroll bar.
 * @class VScrollBar
 **/

/**
 * Creates a new `VScrollBar`. `parent` is the owner of the scroll bar.
 * @param {DOMElement} parent A DOM element
 * @param {Object} renderer An editor renderer
 *
 * @constructor
 **/
var VScrollBar = function(parent, renderer) {
    ScrollBar.call(this, parent);
    this.scrollTop = 0;

    // in OSX lion the scrollbars appear to have no width. In this case resize the
    // element to show the scrollbar but still pretend that the scrollbar has a width
    // of 0px
    // in Firefox 6+ scrollbar is hidden if element has the same width as scrollbar
    // make element a little bit wider to retain scrollbar when page is zoomed 
    renderer.$scrollbarWidth = 
    this.width = dom.scrollbarWidth(parent.ownerDocument);
    this.inner.style.width =
    this.element.style.width = (this.width || 15) + 5 + "px";
};

oop.inherits(VScrollBar, ScrollBar);

(function() {

    this.classSuffix = '-v';

    /**
     * Emitted when the scroll bar, well, scrolls.
     * @event scroll
     * @param {Object} e Contains one property, `"data"`, which indicates the current scroll top position
     **/
    this.onScroll = function() {
        if (!this.skipEvent) {
            this.scrollTop = this.element.scrollTop;
            this._emit("scroll", {data: this.scrollTop});
        }
        this.skipEvent = false;
    };

    /**
     * Returns the width of the scroll bar.
     * @returns {Number}
     **/
    this.getWidth = function() {
        return this.isVisible ? this.width : 0;
    };

    /**
     * Sets the height of the scroll bar, in pixels.
     * @param {Number} height The new height
     **/
    this.setHeight = function(height) {
        this.element.style.height = height + "px";
    };

    /**
     * Sets the inner height of the scroll bar, in pixels.
     * @param {Number} height The new inner height
     * @deprecated Use setScrollHeight instead
     **/
    this.setInnerHeight = function(height) {
        this.inner.style.height = height + "px";
    };

    /**
     * Sets the scroll height of the scroll bar, in pixels.
     * @param {Number} height The new scroll height
     **/
    this.setScrollHeight = function(height) {
        this.inner.style.height = height + "px";
    };

    /**
     * Sets the scroll top of the scroll bar.
     * @param {Number} scrollTop The new scroll top
     **/
    this.setScrollTop = function(scrollTop) {
        // on chrome 17+ for small zoom levels after calling this function
        // this.element.scrollTop != scrollTop which makes page to scroll up.
        if (this.scrollTop != scrollTop) {
            this.skipEvent = true;
            this.scrollTop = this.element.scrollTop = scrollTop;
        }
    };

}).call(VScrollBar.prototype);

/**
 * Represents a horisontal scroll bar.
 * @class HScrollBar
 **/

/**
 * Creates a new `HScrollBar`. `parent` is the owner of the scroll bar.
 * @param {DOMElement} parent A DOM element
 * @param {Object} renderer An editor renderer
 *
 * @constructor
 **/
var HScrollBar = function(parent, renderer) {
    ScrollBar.call(this, parent);
    this.scrollLeft = 0;

    // in OSX lion the scrollbars appear to have no width. In this case resize the
    // element to show the scrollbar but still pretend that the scrollbar has a width
    // of 0px
    // in Firefox 6+ scrollbar is hidden if element has the same width as scrollbar
    // make element a little bit wider to retain scrollbar when page is zoomed 
    this.height = renderer.$scrollbarWidth;
    this.inner.style.height =
    this.element.style.height = (this.height || 15) + 5 + "px";
};

oop.inherits(HScrollBar, ScrollBar);

(function() {

    this.classSuffix = '-h';

    /**
     * Emitted when the scroll bar, well, scrolls.
     * @event scroll
     * @param {Object} e Contains one property, `"data"`, which indicates the current scroll left position
     **/
    this.onScroll = function() {
        if (!this.skipEvent) {
            this.scrollLeft = this.element.scrollLeft;
            this._emit("scroll", {data: this.scrollLeft});
        }
        this.skipEvent = false;
    };

    /**
     * Returns the height of the scroll bar.
     * @returns {Number}
     **/
    this.getHeight = function() {
        return this.isVisible ? this.height : 0;
    };

    /**
     * Sets the width of the scroll bar, in pixels.
     * @param {Number} width The new width
     **/
    this.setWidth = function(width) {
        this.element.style.width = width + "px";
    };

    /**
     * Sets the inner width of the scroll bar, in pixels.
     * @param {Number} width The new inner width
     * @deprecated Use setScrollWidth instead
     **/
    this.setInnerWidth = function(width) {
        this.inner.style.width = width + "px";
    };

    /**
     * Sets the scroll width of the scroll bar, in pixels.
     * @param {Number} width The new scroll width
     **/
    this.setScrollWidth = function(width) {
        this.inner.style.width = width + "px";
    };

    /**
     * Sets the scroll left of the scroll bar.
     * @param {Number} scrollTop The new scroll left
     **/
    this.setScrollLeft = function(scrollLeft) {
        // on chrome 17+ for small zoom levels after calling this function
        // this.element.scrollTop != scrollTop which makes page to scroll up.
        if (this.scrollLeft != scrollLeft) {
            this.skipEvent = true;
            this.scrollLeft = this.element.scrollLeft = scrollLeft;
        }
    };

}).call(HScrollBar.prototype);


exports.ScrollBar = VScrollBar; // backward compatibility
exports.ScrollBarV = VScrollBar; // backward compatibility
exports.ScrollBarH = HScrollBar; // backward compatibility

exports.VScrollBar = VScrollBar;
exports.HScrollBar = HScrollBar;
});
