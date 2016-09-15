/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set shiftwidth=2 tabstop=2 autoindent cindent expandtab: */
/* Copyright 2012 Mozilla Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

'use strict';

/**
 * @typedef {Object} PDFOutlineViewOptions
 * @property {HTMLDivElement} container - The viewer element.
 * @property {Array} outline - An array of outline objects.
 * @property {IPDFLinkService} linkService - The navigation/linking service.
 */

/**
 * @class
 */
var PDFOutlineView = (function PDFOutlineViewClosure() {
  /**
   * @constructs PDFOutlineView
   * @param {PDFOutlineViewOptions} options
   */
  function PDFOutlineView(options) {
    this.container = options.container;
    this.outline = options.outline;
    this.linkService = options.linkService;
  }

  PDFOutlineView.prototype = {
    reset: function PDFOutlineView_reset() {
      var container = this.container;
      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
    },

    /**
     * @private
     */
    _dispatchEvent: function PDFOutlineView_dispatchEvent(outlineCount) {
      var event = document.createEvent('CustomEvent');
      event.initCustomEvent('outlineloaded', true, true, {
        outlineCount: outlineCount
      });
      this.container.dispatchEvent(event);
    },

    /**
     * @private
     */
    _bindLink: function PDFOutlineView_bindLink(element, item) {
      var linkService = this.linkService;
      element.href = linkService.getDestinationHash(item.dest);
      element.onclick = function goToDestination(e) {
        linkService.navigateTo(item.dest);
        return false;
      };
    },

    render: function PDFOutlineView_render() {
      var outline = this.outline;
      var outlineCount = 0;

      this.reset();

      if (!outline) {
        this._dispatchEvent(outlineCount);
        return;
      }

      var queue = [{ parent: this.container, items: this.outline }];
      while (queue.length > 0) {
        var levelData = queue.shift();
        for (var i = 0, len = levelData.items.length; i < len; i++) {
          var item = levelData.items[i];
          var div = document.createElement('div');
          div.className = 'outlineItem';
          var element = document.createElement('a');
          this._bindLink(element, item);
          element.textContent = item.title;
          div.appendChild(element);

          if (item.items.length > 0) {
            var itemsDiv = document.createElement('div');
            itemsDiv.className = 'outlineItems';
            div.appendChild(itemsDiv);
            queue.push({ parent: itemsDiv, items: item.items });
          }

          levelData.parent.appendChild(div);
          outlineCount++;
        }
      }

      this._dispatchEvent(outlineCount);
    }
  };

  return PDFOutlineView;
})();
