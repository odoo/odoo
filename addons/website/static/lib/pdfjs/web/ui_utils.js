/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
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

var CSS_UNITS = 96.0 / 72.0;
var DEFAULT_SCALE = 'auto';
var UNKNOWN_SCALE = 0;
var MAX_AUTO_SCALE = 1.25;
var SCROLLBAR_PADDING = 40;
var VERTICAL_PADDING = 5;

// optimised CSS custom property getter/setter
var CustomStyle = (function CustomStyleClosure() {

  // As noted on: http://www.zachstronaut.com/posts/2009/02/17/
  //              animate-css-transforms-firefox-webkit.html
  // in some versions of IE9 it is critical that ms appear in this list
  // before Moz
  var prefixes = ['ms', 'Moz', 'Webkit', 'O'];
  var _cache = {};

  function CustomStyle() {}

  CustomStyle.getProp = function get(propName, element) {
    // check cache only when no element is given
    if (arguments.length === 1 && typeof _cache[propName] === 'string') {
      return _cache[propName];
    }

    element = element || document.documentElement;
    var style = element.style, prefixed, uPropName;

    // test standard property first
    if (typeof style[propName] === 'string') {
      return (_cache[propName] = propName);
    }

    // capitalize
    uPropName = propName.charAt(0).toUpperCase() + propName.slice(1);

    // test vendor specific properties
    for (var i = 0, l = prefixes.length; i < l; i++) {
      prefixed = prefixes[i] + uPropName;
      if (typeof style[prefixed] === 'string') {
        return (_cache[propName] = prefixed);
      }
    }

    //if all fails then set to undefined
    return (_cache[propName] = 'undefined');
  };

  CustomStyle.setProp = function set(propName, element, str) {
    var prop = this.getProp(propName);
    if (prop !== 'undefined') {
      element.style[prop] = str;
    }
  };

  return CustomStyle;
})();

function getFileName(url) {
  var anchor = url.indexOf('#');
  var query = url.indexOf('?');
  var end = Math.min(
    anchor > 0 ? anchor : url.length,
    query > 0 ? query : url.length);
  return url.substring(url.lastIndexOf('/', end) + 1, end);
}

/**
 * Returns scale factor for the canvas. It makes sense for the HiDPI displays.
 * @return {Object} The object with horizontal (sx) and vertical (sy)
                    scales. The scaled property is set to false if scaling is
                    not required, true otherwise.
 */
function getOutputScale(ctx) {
  var devicePixelRatio = window.devicePixelRatio || 1;
  var backingStoreRatio = ctx.webkitBackingStorePixelRatio ||
                          ctx.mozBackingStorePixelRatio ||
                          ctx.msBackingStorePixelRatio ||
                          ctx.oBackingStorePixelRatio ||
                          ctx.backingStorePixelRatio || 1;
  var pixelRatio = devicePixelRatio / backingStoreRatio;
  return {
    sx: pixelRatio,
    sy: pixelRatio,
    scaled: pixelRatio !== 1
  };
}

/**
 * Scrolls specified element into view of its parent.
 * element {Object} The element to be visible.
 * spot {Object} An object with optional top and left properties,
 *               specifying the offset from the top left edge.
 */
function scrollIntoView(element, spot) {
  // Assuming offsetParent is available (it's not available when viewer is in
  // hidden iframe or object). We have to scroll: if the offsetParent is not set
  // producing the error. See also animationStartedClosure.
  var parent = element.offsetParent;
  var offsetY = element.offsetTop + element.clientTop;
  var offsetX = element.offsetLeft + element.clientLeft;
  if (!parent) {
    console.error('offsetParent is not set -- cannot scroll');
    return;
  }
  while (parent.clientHeight === parent.scrollHeight) {
    if (parent.dataset._scaleY) {
      offsetY /= parent.dataset._scaleY;
      offsetX /= parent.dataset._scaleX;
    }
    offsetY += parent.offsetTop;
    offsetX += parent.offsetLeft;
    parent = parent.offsetParent;
    if (!parent) {
      return; // no need to scroll
    }
  }
  if (spot) {
    if (spot.top !== undefined) {
      offsetY += spot.top;
    }
    if (spot.left !== undefined) {
      offsetX += spot.left;
      parent.scrollLeft = offsetX;
    }
  }
  parent.scrollTop = offsetY;
}

/**
 * Helper function to start monitoring the scroll event and converting them into
 * PDF.js friendly one: with scroll debounce and scroll direction.
 */
function watchScroll(viewAreaElement, callback) {
  var debounceScroll = function debounceScroll(evt) {
    if (rAF) {
      return;
    }
    // schedule an invocation of scroll for next animation frame.
    rAF = window.requestAnimationFrame(function viewAreaElementScrolled() {
      rAF = null;

      var currentY = viewAreaElement.scrollTop;
      var lastY = state.lastY;
      if (currentY !== lastY) {
        state.down = currentY > lastY;
      }
      state.lastY = currentY;
      callback(state);
    });
  };

  var state = {
    down: true,
    lastY: viewAreaElement.scrollTop,
    _eventHandler: debounceScroll
  };

  var rAF = null;
  viewAreaElement.addEventListener('scroll', debounceScroll, true);
  return state;
}

/**
 * Use binary search to find the index of the first item in a given array which
 * passes a given condition. The items are expected to be sorted in the sense
 * that if the condition is true for one item in the array, then it is also true
 * for all following items.
 *
 * @returns {Number} Index of the first array element to pass the test,
 *                   or |items.length| if no such element exists.
 */
function binarySearchFirstItem(items, condition) {
  var minIndex = 0;
  var maxIndex = items.length - 1;

  if (items.length === 0 || !condition(items[maxIndex])) {
    return items.length;
  }
  if (condition(items[minIndex])) {
    return minIndex;
  }

  while (minIndex < maxIndex) {
    var currentIndex = (minIndex + maxIndex) >> 1;
    var currentItem = items[currentIndex];
    if (condition(currentItem)) {
      maxIndex = currentIndex;
    } else {
      minIndex = currentIndex + 1;
    }
  }
  return minIndex; /* === maxIndex */
}

/**
 * Generic helper to find out what elements are visible within a scroll pane.
 */
function getVisibleElements(scrollEl, views, sortByVisibility) {
  var top = scrollEl.scrollTop, bottom = top + scrollEl.clientHeight;
  var left = scrollEl.scrollLeft, right = left + scrollEl.clientWidth;

  function isElementBottomBelowViewTop(view) {
    var element = view.div;
    var elementBottom =
      element.offsetTop + element.clientTop + element.clientHeight;
    return elementBottom > top;
  }

  var visible = [], view, element;
  var currentHeight, viewHeight, hiddenHeight, percentHeight;
  var currentWidth, viewWidth;
  var firstVisibleElementInd = (views.length === 0) ? 0 :
    binarySearchFirstItem(views, isElementBottomBelowViewTop);

  for (var i = firstVisibleElementInd, ii = views.length; i < ii; i++) {
    view = views[i];
    element = view.div;
    currentHeight = element.offsetTop + element.clientTop;
    viewHeight = element.clientHeight;

    if (currentHeight > bottom) {
      break;
    }

    currentWidth = element.offsetLeft + element.clientLeft;
    viewWidth = element.clientWidth;
    if (currentWidth + viewWidth < left || currentWidth > right) {
      continue;
    }
    hiddenHeight = Math.max(0, top - currentHeight) +
      Math.max(0, currentHeight + viewHeight - bottom);
    percentHeight = ((viewHeight - hiddenHeight) * 100 / viewHeight) | 0;

    visible.push({
      id: view.id,
      x: currentWidth,
      y: currentHeight,
      view: view,
      percent: percentHeight
    });
  }

  var first = visible[0];
  var last = visible[visible.length - 1];

  if (sortByVisibility) {
    visible.sort(function(a, b) {
      var pc = a.percent - b.percent;
      if (Math.abs(pc) > 0.001) {
        return -pc;
      }
      return a.id - b.id; // ensure stability
    });
  }
  return {first: first, last: last, views: visible};
}

/**
 * Event handler to suppress context menu.
 */
function noContextMenuHandler(e) {
  e.preventDefault();
}

/**
 * Returns the filename or guessed filename from the url (see issue 3455).
 * url {String} The original PDF location.
 * @return {String} Guessed PDF file name.
 */
function getPDFFileNameFromURL(url) {
  var reURI = /^(?:([^:]+:)?\/\/[^\/]+)?([^?#]*)(\?[^#]*)?(#.*)?$/;
  //            SCHEME      HOST         1.PATH  2.QUERY   3.REF
  // Pattern to get last matching NAME.pdf
  var reFilename = /[^\/?#=]+\.pdf\b(?!.*\.pdf\b)/i;
  var splitURI = reURI.exec(url);
  var suggestedFilename = reFilename.exec(splitURI[1]) ||
                           reFilename.exec(splitURI[2]) ||
                           reFilename.exec(splitURI[3]);
  if (suggestedFilename) {
    suggestedFilename = suggestedFilename[0];
    if (suggestedFilename.indexOf('%') !== -1) {
      // URL-encoded %2Fpath%2Fto%2Ffile.pdf should be file.pdf
      try {
        suggestedFilename =
          reFilename.exec(decodeURIComponent(suggestedFilename))[0];
      } catch(e) { // Possible (extremely rare) errors:
        // URIError "Malformed URI", e.g. for "%AA.pdf"
        // TypeError "null has no properties", e.g. for "%2F.pdf"
      }
    }
  }
  return suggestedFilename || 'document.pdf';
}

var ProgressBar = (function ProgressBarClosure() {

  function clamp(v, min, max) {
    return Math.min(Math.max(v, min), max);
  }

  function ProgressBar(id, opts) {
    this.visible = true;

    // Fetch the sub-elements for later.
    this.div = document.querySelector(id + ' .progress');

    // Get the loading bar element, so it can be resized to fit the viewer.
    this.bar = this.div.parentNode;

    // Get options, with sensible defaults.
    this.height = opts.height || 100;
    this.width = opts.width || 100;
    this.units = opts.units || '%';

    // Initialize heights.
    this.div.style.height = this.height + this.units;
    this.percent = 0;
  }

  ProgressBar.prototype = {

    updateBar: function ProgressBar_updateBar() {
      if (this._indeterminate) {
        this.div.classList.add('indeterminate');
        this.div.style.width = this.width + this.units;
        return;
      }

      this.div.classList.remove('indeterminate');
      var progressSize = this.width * this._percent / 100;
      this.div.style.width = progressSize + this.units;
    },

    get percent() {
      return this._percent;
    },

    set percent(val) {
      this._indeterminate = isNaN(val);
      this._percent = clamp(val, 0, 100);
      this.updateBar();
    },

    setWidth: function ProgressBar_setWidth(viewer) {
      if (viewer) {
        var container = viewer.parentNode;
        var scrollbarWidth = container.offsetWidth - viewer.offsetWidth;
        if (scrollbarWidth > 0) {
          this.bar.setAttribute('style', 'width: calc(100% - ' +
                                         scrollbarWidth + 'px);');
        }
      }
    },

    hide: function ProgressBar_hide() {
      if (!this.visible) {
        return;
      }
      this.visible = false;
      this.bar.classList.add('hidden');
      document.body.classList.remove('loadingInProgress');
    },

    show: function ProgressBar_show() {
      if (this.visible) {
        return;
      }
      this.visible = true;
      document.body.classList.add('loadingInProgress');
      this.bar.classList.remove('hidden');
    }
  };

  return ProgressBar;
})();
