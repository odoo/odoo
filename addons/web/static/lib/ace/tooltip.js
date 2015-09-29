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

/**
 * @class Tooltip
 **/

/**
 * @param {Element} parentNode
 *
 * @constructor
 **/
function Tooltip (parentNode) {
    this.isOpen = false;
    this.$element = null;
    this.$parentNode = parentNode;
}

(function() {
    this.$init = function() {
        this.$element = dom.createElement("div");
        this.$element.className = "ace_tooltip";
        this.$element.style.display = "none";
        this.$parentNode.appendChild(this.$element);
        return this.$element;
    };

    /**
     * @returns {Element}
     **/
    this.getElement = function() {
        return this.$element || this.$init();
    };

    /**
     * @param {String} text
     **/
    this.setText = function(text) {
        dom.setInnerText(this.getElement(), text);
    };

    /**
     * @param {String} html
     **/
    this.setHtml = function(html) {
        this.getElement().innerHTML = html;
    };

    /**
     * @param {Number} x
     * @param {Number} y
     **/
    this.setPosition = function(x, y) {
        this.getElement().style.left = x + "px";
        this.getElement().style.top = y + "px";
    };

    /**
     * @param {String} className
     **/
    this.setClassName = function(className) {
        dom.addCssClass(this.getElement(), className);
    };

    /**
     * @param {String} text
     * @param {Number} x
     * @param {Number} y
     **/
    this.show = function(text, x, y) {
        if (text != null)
            this.setText(text);
        if (x != null && y != null)
            this.setPosition(x, y);
        if (!this.isOpen) {
            this.getElement().style.display = "block";
            this.isOpen = true;
        }
    };

    this.hide = function() {
        if (this.isOpen) {
            this.getElement().style.display = "none";
            this.isOpen = false;
        }
    };

    /**
     * @returns {Number}
     **/
    this.getHeight = function() {
        return this.getElement().offsetHeight;
    };

    /**
     * @returns {Number}
     **/
    this.getWidth = function() {
        return this.getElement().offsetWidth;
    };

}).call(Tooltip.prototype);

exports.Tooltip = Tooltip;
});
