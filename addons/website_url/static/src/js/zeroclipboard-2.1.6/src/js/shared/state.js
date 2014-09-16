/*jshint -W079 */

/**
 * Store references to critically important global functions that may be
 * overridden on certain web pages.
 */
var _window = window,
    _document = _window.document,
    _navigator = _window.navigator,
    _setTimeout = _window.setTimeout,
    _encodeURIComponent = _window.encodeURIComponent,
    _ActiveXObject = _window.ActiveXObject,
    _Error = _window.Error,
    _parseInt = _window.Number.parseInt || _window.parseInt,
    _parseFloat = _window.Number.parseFloat || _window.parseFloat,
    _isNaN = _window.Number.isNaN || _window.isNaN,
    _round = _window.Math.round,
    _now = _window.Date.now,
    _keys = _window.Object.keys,
    _defineProperty = _window.Object.defineProperty,
    _hasOwn = _window.Object.prototype.hasOwnProperty,
    _slice = _window.Array.prototype.slice,
    _unwrap = (function() {
      var unwrapper = function(el) {
        return el;
      };
      // For Polymer
      if (typeof _window.wrap === "function" && typeof _window.unwrap === "function") {
        try {
          var div = _document.createElement("div");
          var unwrappedDiv = _window.unwrap(div);
          if (div.nodeType === 1 && unwrappedDiv && unwrappedDiv.nodeType === 1) {
            unwrapper = _window.unwrap;
          }
        }
        catch (e) {
          // Some unreliable `window.unwrap` function is exposed
        }
      }
      return unwrapper;
    })();
