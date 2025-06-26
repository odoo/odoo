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

/**
 * Define a module along with a payload
 * @param module a name for the payload
 * @param payload a function to call with (require, exports, module) params
 */

(function () {
  var ACE_NAMESPACE = "";

  var global = (function () {
    return this;
  })();
  if (!global && typeof window != "undefined") global = window; // strict mode

  if (!ACE_NAMESPACE && typeof requirejs !== "undefined") return;

  var define = function (module, deps, payload) {
    if (typeof module !== "string") {
      if (define.original) define.original.apply(this, arguments);
      else {
        console.error("dropping module because define wasn't a string.");
        console.trace();
      }
      return;
    }
    if (arguments.length == 2) payload = deps;
    if (!define.modules[module]) {
      define.payloads[module] = payload;
      define.modules[module] = null;
    }
  };

  define.modules = {};
  define.payloads = {};

  /**
   * Get at functionality define()ed using the function above
   */
  var _require = function (parentId, module, callback) {
    if (typeof module === "string") {
      var payload = lookup(parentId, module);
      if (payload != undefined) {
        callback && callback();
        return payload;
      }
    } else if (Object.prototype.toString.call(module) === "[object Array]") {
      var params = [];
      for (var i = 0, l = module.length; i < l; ++i) {
        var dep = lookup(parentId, module[i]);
        if (dep == undefined && require.original) return;
        params.push(dep);
      }
      return (callback && callback.apply(null, params)) || true;
    }
  };

  var require = function (module, callback) {
    var packagedModule = _require("", module, callback);
    if (packagedModule == undefined && require.original)
      return require.original.apply(this, arguments);
    return packagedModule;
  };

  var normalizeModule = function (parentId, moduleName) {
    // normalize plugin requires
    if (moduleName.indexOf("!") !== -1) {
      var chunks = moduleName.split("!");
      return (
        normalizeModule(parentId, chunks[0]) +
        "!" +
        normalizeModule(parentId, chunks[1])
      );
    }
    // normalize relative requires
    if (moduleName.charAt(0) == ".") {
      var base = parentId.split("/").slice(0, -1).join("/");
      moduleName = base + "/" + moduleName;

      while (moduleName.indexOf(".") !== -1 && previous != moduleName) {
        var previous = moduleName;
        moduleName = moduleName
          .replace(/\/\.\//, "/")
          .replace(/[^\/]+\/\.\.\//, "");
      }
    }
    return moduleName;
  };

  /**
   * Internal function to lookup moduleNames and resolve them by calling the
   * definition function if needed.
   */
  var lookup = function (parentId, moduleName) {
    moduleName = normalizeModule(parentId, moduleName);

    var module = define.modules[moduleName];
    if (!module) {
      module = define.payloads[moduleName];
      if (typeof module === "function") {
        var exports = {};
        var mod = {
          id: moduleName,
          uri: "",
          exports: exports,
          packaged: true,
        };

        var req = function (module, callback) {
          return _require(moduleName, module, callback);
        };

        var returnValue = module(req, exports, mod);
        exports = returnValue || mod.exports;
        define.modules[moduleName] = exports;
        delete define.payloads[moduleName];
      }
      module = define.modules[moduleName] = exports || module;
    }
    return module;
  };

  function exportAce(ns) {
    var root = global;
    if (ns) {
      if (!global[ns]) global[ns] = {};
      root = global[ns];
    }

    if (!root.define || !root.define.packaged) {
      define.original = root.define;
      root.define = define;
      root.define.packaged = true;
    }

    if (!root.require || !root.require.packaged) {
      require.original = root.require;
      root.require = require;
      root.require.packaged = true;
    }
  }

  exportAce(ACE_NAMESPACE);
})();

define("ace/lib/es6-shim", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  function defineProp(obj, name, val) {
    Object.defineProperty(obj, name, {
      value: val,
      enumerable: false,
      writable: true,
      configurable: true,
    });
  }
  if (!String.prototype.startsWith) {
    defineProp(
      String.prototype,
      "startsWith",
      function (searchString, position) {
        position = position || 0;
        return this.lastIndexOf(searchString, position) === position;
      },
    );
  }
  if (!String.prototype.endsWith) {
    defineProp(String.prototype, "endsWith", function (searchString, position) {
      var subjectString = this;
      if (position === undefined || position > subjectString.length) {
        position = subjectString.length;
      }
      position -= searchString.length;
      var lastIndex = subjectString.indexOf(searchString, position);
      return lastIndex !== -1 && lastIndex === position;
    });
  }
  if (!String.prototype.repeat) {
    defineProp(String.prototype, "repeat", function (count) {
      var result = "";
      var string = this;
      while (count > 0) {
        if (count & 1) result += string;
        if ((count >>= 1)) string += string;
      }
      return result;
    });
  }
  if (!String.prototype.includes) {
    defineProp(String.prototype, "includes", function (str, position) {
      return this.indexOf(str, position) != -1;
    });
  }
  if (!Object.assign) {
    Object.assign = function (target) {
      if (target === undefined || target === null) {
        throw new TypeError("Cannot convert undefined or null to object");
      }
      var output = Object(target);
      for (var index = 1; index < arguments.length; index++) {
        var source = arguments[index];
        if (source !== undefined && source !== null) {
          Object.keys(source).forEach(function (key) {
            output[key] = source[key];
          });
        }
      }
      return output;
    };
  }
  if (!Object.values) {
    Object.values = function (o) {
      return Object.keys(o).map(function (k) {
        return o[k];
      });
    };
  }
  if (!Array.prototype.find) {
    defineProp(Array.prototype, "find", function (predicate) {
      var len = this.length;
      var thisArg = arguments[1];
      for (var k = 0; k < len; k++) {
        var kValue = this[k];
        if (predicate.call(thisArg, kValue, k, this)) {
          return kValue;
        }
      }
    });
  }
  if (!Array.prototype.findIndex) {
    defineProp(Array.prototype, "findIndex", function (predicate) {
      var len = this.length;
      var thisArg = arguments[1];
      for (var k = 0; k < len; k++) {
        var kValue = this[k];
        if (predicate.call(thisArg, kValue, k, this)) {
          return k;
        }
      }
    });
  }
  if (!Array.prototype.includes) {
    defineProp(Array.prototype, "includes", function (item, position) {
      return this.indexOf(item, position) != -1;
    });
  }
  if (!Array.prototype.fill) {
    defineProp(Array.prototype, "fill", function (value) {
      var O = this;
      var len = O.length >>> 0;
      var start = arguments[1];
      var relativeStart = start >> 0;
      var k =
        relativeStart < 0
          ? Math.max(len + relativeStart, 0)
          : Math.min(relativeStart, len);
      var end = arguments[2];
      var relativeEnd = end === undefined ? len : end >> 0;
      var final =
        relativeEnd < 0
          ? Math.max(len + relativeEnd, 0)
          : Math.min(relativeEnd, len);
      while (k < final) {
        O[k] = value;
        k++;
      }
      return O;
    });
  }
  if (!Array.of) {
    defineProp(Array, "of", function () {
      return Array.prototype.slice.call(arguments);
    });
  }
});

define("ace/lib/fixoldbrowsers", [
  "require",
  "exports",
  "module",
  "ace/lib/es6-shim",
], function (require, exports, module) {
  // vim:set ts=4 sts=4 sw=4 st:
  "use strict";
  require("./es6-shim");
});

define("ace/lib/deep_copy", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  exports.deepCopy = function deepCopy(obj) {
    if (typeof obj !== "object" || !obj) return obj;
    var copy;
    if (Array.isArray(obj)) {
      copy = [];
      for (var key = 0; key < obj.length; key++) {
        copy[key] = deepCopy(obj[key]);
      }
      return copy;
    }
    if (Object.prototype.toString.call(obj) !== "[object Object]") return obj;
    copy = {};
    for (var key in obj) copy[key] = deepCopy(obj[key]);
    return copy;
  };
});

define("ace/lib/lang", [
  "require",
  "exports",
  "module",
  "ace/lib/deep_copy",
], function (require, exports, module) {
  "use strict";
  exports.last = function (a) {
    return a[a.length - 1];
  };
  exports.stringReverse = function (string) {
    return string.split("").reverse().join("");
  };
  exports.stringRepeat = function (string, count) {
    var result = "";
    while (count > 0) {
      if (count & 1) result += string;
      if ((count >>= 1)) string += string;
    }
    return result;
  };
  var trimBeginRegexp = /^\s\s*/;
  var trimEndRegexp = /\s\s*$/;
  exports.stringTrimLeft = function (string) {
    return string.replace(trimBeginRegexp, "");
  };
  exports.stringTrimRight = function (string) {
    return string.replace(trimEndRegexp, "");
  };
  exports.copyObject = function (obj) {
    var copy = {};
    for (var key in obj) {
      copy[key] = obj[key];
    }
    return copy;
  };
  exports.copyArray = function (array) {
    var copy = [];
    for (var i = 0, l = array.length; i < l; i++) {
      if (array[i] && typeof array[i] == "object")
        copy[i] = this.copyObject(array[i]);
      else copy[i] = array[i];
    }
    return copy;
  };
  exports.deepCopy = require("./deep_copy").deepCopy;
  exports.arrayToMap = function (arr) {
    var map = {};
    for (var i = 0; i < arr.length; i++) {
      map[arr[i]] = 1;
    }
    return map;
  };
  exports.createMap = function (props) {
    var map = Object.create(null);
    for (var i in props) {
      map[i] = props[i];
    }
    return map;
  };
  exports.arrayRemove = function (array, value) {
    for (var i = 0; i <= array.length; i++) {
      if (value === array[i]) {
        array.splice(i, 1);
      }
    }
  };
  exports.escapeRegExp = function (str) {
    return str.replace(/([.*+?^${}()|[\]\/\\])/g, "\\$1");
  };
  exports.escapeHTML = function (str) {
    return ("" + str)
      .replace(/&/g, "&#38;")
      .replace(/"/g, "&#34;")
      .replace(/'/g, "&#39;")
      .replace(/</g, "&#60;");
  };
  exports.getMatchOffsets = function (string, regExp) {
    var matches = [];
    string.replace(regExp, function (str) {
      matches.push({
        offset: arguments[arguments.length - 2],
        length: str.length,
      });
    });
    return matches;
  };
  exports.deferredCall = function (fcn) {
    var timer = null;
    var callback = function () {
      timer = null;
      fcn();
    };
    var deferred = function (timeout) {
      deferred.cancel();
      timer = setTimeout(callback, timeout || 0);
      return deferred;
    };
    deferred.schedule = deferred;
    deferred.call = function () {
      this.cancel();
      fcn();
      return deferred;
    };
    deferred.cancel = function () {
      clearTimeout(timer);
      timer = null;
      return deferred;
    };
    deferred.isPending = function () {
      return timer;
    };
    return deferred;
  };
  exports.delayedCall = function (fcn, defaultTimeout) {
    var timer = null;
    var callback = function () {
      timer = null;
      fcn();
    };
    var _self = function (timeout) {
      if (timer == null)
        timer = setTimeout(callback, timeout || defaultTimeout);
    };
    _self.delay = function (timeout) {
      timer && clearTimeout(timer);
      timer = setTimeout(callback, timeout || defaultTimeout);
    };
    _self.schedule = _self;
    _self.call = function () {
      this.cancel();
      fcn();
    };
    _self.cancel = function () {
      timer && clearTimeout(timer);
      timer = null;
    };
    _self.isPending = function () {
      return timer;
    };
    return _self;
  };
  exports.supportsLookbehind = function () {
    try {
      new RegExp("(?<=.)");
    } catch (e) {
      return false;
    }
    return true;
  };
  exports.skipEmptyMatch = function (line, last, supportsUnicodeFlag) {
    return supportsUnicodeFlag && line.codePointAt(last) > 0xffff ? 2 : 1;
  };
});

define("ace/lib/useragent", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  "use strict";
  exports.OS = {
    LINUX: "LINUX",
    MAC: "MAC",
    WINDOWS: "WINDOWS",
  };
  exports.getOS = function () {
    if (exports.isMac) {
      return exports.OS.MAC;
    } else if (exports.isLinux) {
      return exports.OS.LINUX;
    } else {
      return exports.OS.WINDOWS;
    }
  };
  var _navigator = typeof navigator == "object" ? navigator : {};
  var os = (/mac|win|linux/i.exec(_navigator.platform) || [
    "other",
  ])[0].toLowerCase();
  var ua = _navigator.userAgent || "";
  var appName = _navigator.appName || "";
  exports.isWin = os == "win";
  exports.isMac = os == "mac";
  exports.isLinux = os == "linux";
  exports.isIE =
    appName == "Microsoft Internet Explorer" ||
    appName.indexOf("MSAppHost") >= 0
      ? parseFloat(
          (ua.match(
            /(?:MSIE |Trident\/[0-9]+[\.0-9]+;.*rv:)([0-9]+[\.0-9]+)/,
          ) || [])[1],
        )
      : parseFloat(
          (ua.match(/(?:Trident\/[0-9]+[\.0-9]+;.*rv:)([0-9]+[\.0-9]+)/) ||
            [])[1],
        ); // for ie
  exports.isOldIE = exports.isIE && exports.isIE < 9;
  exports.isGecko = exports.isMozilla = ua.match(/ Gecko\/\d+/);
  exports.isOpera =
    typeof opera == "object" &&
    Object.prototype.toString.call(window["opera"]) == "[object Opera]";
  exports.isWebKit = parseFloat(ua.split("WebKit/")[1]) || undefined;
  exports.isChrome = parseFloat(ua.split(" Chrome/")[1]) || undefined;
  exports.isSafari =
    (parseFloat(ua.split(" Safari/")[1]) && !exports.isChrome) || undefined;
  exports.isEdge = parseFloat(ua.split(" Edge/")[1]) || undefined;
  exports.isAIR = ua.indexOf("AdobeAIR") >= 0;
  exports.isAndroid = ua.indexOf("Android") >= 0;
  exports.isChromeOS = ua.indexOf(" CrOS ") >= 0;
  exports.isIOS = /iPad|iPhone|iPod/.test(ua) && !window["MSStream"];
  if (exports.isIOS) exports.isMac = true;
  exports.isMobile = exports.isIOS || exports.isAndroid;
});

define("ace/lib/dom", [
  "require",
  "exports",
  "module",
  "ace/lib/useragent",
], function (require, exports, module) {
  "use strict";
  var useragent = require("./useragent");
  var XHTML_NS = "http://www.w3.org/1999/xhtml";
  exports.buildDom = function buildDom(arr, parent, refs) {
    if (typeof arr == "string" && arr) {
      var txt = document.createTextNode(arr);
      if (parent) parent.appendChild(txt);
      return txt;
    }
    if (!Array.isArray(arr)) {
      if (arr && arr.appendChild && parent) parent.appendChild(arr);
      return arr;
    }
    if (typeof arr[0] != "string" || !arr[0]) {
      var els = [];
      for (var i = 0; i < arr.length; i++) {
        var ch = buildDom(arr[i], parent, refs);
        ch && els.push(ch);
      }
      return els;
    }
    var el = document.createElement(arr[0]);
    var options = arr[1];
    var childIndex = 1;
    if (options && typeof options == "object" && !Array.isArray(options))
      childIndex = 2;
    for (var i = childIndex; i < arr.length; i++) buildDom(arr[i], el, refs);
    if (childIndex == 2) {
      Object.keys(options).forEach(function (n) {
        var val = options[n];
        if (n === "class") {
          el.className = Array.isArray(val) ? val.join(" ") : val;
        } else if (typeof val == "function" || n == "value" || n[0] == "$") {
          el[n] = val;
        } else if (n === "ref") {
          if (refs) refs[val] = el;
        } else if (n === "style") {
          if (typeof val == "string") el.style.cssText = val;
        } else if (val != null) {
          el.setAttribute(n, val);
        }
      });
    }
    if (parent) parent.appendChild(el);
    return el;
  };
  exports.getDocumentHead = function (doc) {
    if (!doc) doc = document;
    return (
      doc.head || doc.getElementsByTagName("head")[0] || doc.documentElement
    );
  };
  exports.createElement = function (tag, ns) {
    return document.createElementNS
      ? document.createElementNS(ns || XHTML_NS, tag)
      : document.createElement(tag);
  };
  exports.removeChildren = function (element) {
    element.innerHTML = "";
  };
  exports.createTextNode = function (textContent, element) {
    var doc = element ? element.ownerDocument : document;
    return doc.createTextNode(textContent);
  };
  exports.createFragment = function (element) {
    var doc = element ? element.ownerDocument : document;
    return doc.createDocumentFragment();
  };
  exports.hasCssClass = function (el, name) {
    var classes = (el.className + "").split(/\s+/g);
    return classes.indexOf(name) !== -1;
  };
  exports.addCssClass = function (el, name) {
    if (!exports.hasCssClass(el, name)) {
      el.className += " " + name;
    }
  };
  exports.removeCssClass = function (el, name) {
    var classes = el.className.split(/\s+/g);
    while (true) {
      var index = classes.indexOf(name);
      if (index == -1) {
        break;
      }
      classes.splice(index, 1);
    }
    el.className = classes.join(" ");
  };
  exports.toggleCssClass = function (el, name) {
    var classes = el.className.split(/\s+/g),
      add = true;
    while (true) {
      var index = classes.indexOf(name);
      if (index == -1) {
        break;
      }
      add = false;
      classes.splice(index, 1);
    }
    if (add) classes.push(name);
    el.className = classes.join(" ");
    return add;
  };
  exports.setCssClass = function (node, className, include) {
    if (include) {
      exports.addCssClass(node, className);
    } else {
      exports.removeCssClass(node, className);
    }
  };
  exports.hasCssString = function (id, doc) {
    var index = 0,
      sheets;
    doc = doc || document;
    if ((sheets = doc.querySelectorAll("style"))) {
      while (index < sheets.length) {
        if (sheets[index++].id === id) {
          return true;
        }
      }
    }
  };
  exports.removeElementById = function (id, doc) {
    doc = doc || document;
    if (doc.getElementById(id)) {
      doc.getElementById(id).remove();
    }
  };
  var strictCSP;
  var cssCache = [];
  exports.useStrictCSP = function (value) {
    strictCSP = value;
    if (value == false) insertPendingStyles();
    else if (!cssCache) cssCache = [];
  };
  function insertPendingStyles() {
    var cache = cssCache;
    cssCache = null;
    cache &&
      cache.forEach(function (item) {
        importCssString(item[0], item[1]);
      });
  }
  function importCssString(cssText, id, target) {
    if (typeof document == "undefined") return;
    if (cssCache) {
      if (target) {
        insertPendingStyles();
      } else if (target === false) {
        return cssCache.push([cssText, id]);
      }
    }
    if (strictCSP) return;
    var container = target;
    if (!target || !target.getRootNode) {
      container = document;
    } else {
      container = target.getRootNode();
      if (!container || container == target) container = document;
    }
    var doc = container.ownerDocument || container;
    if (id && exports.hasCssString(id, container)) return null;
    if (id) cssText += "\n/*# sourceURL=ace/css/" + id + " */";
    var style = exports.createElement("style");
    style.appendChild(doc.createTextNode(cssText));
    if (id) style.id = id;
    if (container == doc) container = exports.getDocumentHead(doc);
    container.insertBefore(style, container.firstChild);
  }
  exports.importCssString = importCssString;
  exports.importCssStylsheet = function (uri, doc) {
    exports.buildDom(
      ["link", { rel: "stylesheet", href: uri }],
      exports.getDocumentHead(doc),
    );
  };
  exports.scrollbarWidth = function (doc) {
    var inner = exports.createElement("ace_inner");
    inner.style.width = "100%";
    inner.style.minWidth = "0px";
    inner.style.height = "200px";
    inner.style.display = "block";
    var outer = exports.createElement("ace_outer");
    var style = outer.style;
    style.position = "absolute";
    style.left = "-10000px";
    style.overflow = "hidden";
    style.width = "200px";
    style.minWidth = "0px";
    style.height = "150px";
    style.display = "block";
    outer.appendChild(inner);
    var body =
      (doc && doc.documentElement) || (document && document.documentElement);
    if (!body) return 0;
    body.appendChild(outer);
    var noScrollbar = inner.offsetWidth;
    style.overflow = "scroll";
    var withScrollbar = inner.offsetWidth;
    if (noScrollbar === withScrollbar) {
      withScrollbar = outer.clientWidth;
    }
    body.removeChild(outer);
    return noScrollbar - withScrollbar;
  };
  exports.computedStyle = function (element, style) {
    return window.getComputedStyle(element, "") || {};
  };
  exports.setStyle = function (styles, property, value) {
    if (styles[property] !== value) {
      styles[property] = value;
    }
  };
  exports.HAS_CSS_ANIMATION = false;
  exports.HAS_CSS_TRANSFORMS = false;
  exports.HI_DPI = useragent.isWin
    ? typeof window !== "undefined" && window.devicePixelRatio >= 1.5
    : true;
  if (useragent.isChromeOS) exports.HI_DPI = false;
  if (typeof document !== "undefined") {
    var div = document.createElement("div");
    if (exports.HI_DPI && div.style.transform !== undefined)
      exports.HAS_CSS_TRANSFORMS = true;
    if (!useragent.isEdge && typeof div.style.animationName !== "undefined")
      exports.HAS_CSS_ANIMATION = true;
    div = null;
  }
  if (exports.HAS_CSS_TRANSFORMS) {
    exports.translate = function (element, tx, ty) {
      element.style.transform =
        "translate(" + Math.round(tx) + "px, " + Math.round(ty) + "px)";
    };
  } else {
    exports.translate = function (element, tx, ty) {
      element.style.top = Math.round(ty) + "px";
      element.style.left = Math.round(tx) + "px";
    };
  }
});

define("ace/lib/net", [
  "require",
  "exports",
  "module",
  "ace/lib/dom",
], function (require, exports, module) {
  /*
   * based on code from:
   *
   * @license RequireJS text 0.25.0 Copyright (c) 2010-2011, The Dojo Foundation All Rights Reserved.
   * Available via the MIT or new BSD license.
   * see: http://github.com/jrburke/requirejs for details
   */
  "use strict";
  var dom = require("./dom");
  exports.get = function (url, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4) {
        callback(xhr.responseText);
      }
    };
    xhr.send(null);
  };
  exports.loadScript = function (path, callback) {
    var head = dom.getDocumentHead();
    var s = document.createElement("script");
    s.src = path;
    head.appendChild(s);
    s.onload = s.onreadystatechange = function (_, isAbort) {
      if (
        isAbort ||
        !s.readyState ||
        s.readyState == "loaded" ||
        s.readyState == "complete"
      ) {
        s = s.onload = s.onreadystatechange = null;
        if (!isAbort) callback();
      }
    };
  };
  exports.qualifyURL = function (url) {
    var a = document.createElement("a");
    a.href = url;
    return a.href;
  };
});

define("ace/lib/oop", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  "use strict";
  exports.inherits = function (ctor, superCtor) {
    ctor.super_ = superCtor;
    ctor.prototype = Object.create(superCtor.prototype, {
      constructor: {
        value: ctor,
        enumerable: false,
        writable: true,
        configurable: true,
      },
    });
  };
  exports.mixin = function (obj, mixin) {
    for (var key in mixin) {
      obj[key] = mixin[key];
    }
    return obj;
  };
  exports.implement = function (proto, mixin) {
    exports.mixin(proto, mixin);
  };
});

define("ace/lib/event_emitter", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  "use strict";
  var EventEmitter = {};
  var stopPropagation = function () {
    this.propagationStopped = true;
  };
  var preventDefault = function () {
    this.defaultPrevented = true;
  };
  EventEmitter._emit = EventEmitter._dispatchEvent = function (eventName, e) {
    this._eventRegistry || (this._eventRegistry = {});
    this._defaultHandlers || (this._defaultHandlers = {});
    var listeners = this._eventRegistry[eventName] || [];
    var defaultHandler = this._defaultHandlers[eventName];
    if (!listeners.length && !defaultHandler) return;
    if (typeof e != "object" || !e) e = {};
    if (!e.type) e.type = eventName;
    if (!e.stopPropagation) e.stopPropagation = stopPropagation;
    if (!e.preventDefault) e.preventDefault = preventDefault;
    listeners = listeners.slice();
    for (var i = 0; i < listeners.length; i++) {
      listeners[i](e, this);
      if (e.propagationStopped) break;
    }
    if (defaultHandler && !e.defaultPrevented) return defaultHandler(e, this);
  };
  EventEmitter._signal = function (eventName, e) {
    var listeners = (this._eventRegistry || {})[eventName];
    if (!listeners) return;
    listeners = listeners.slice();
    for (var i = 0; i < listeners.length; i++) listeners[i](e, this);
  };
  EventEmitter.once = function (eventName, callback) {
    var _self = this;
    this.on(eventName, function newCallback() {
      _self.off(eventName, newCallback);
      callback.apply(null, arguments);
    });
    if (!callback) {
      return new Promise(function (resolve) {
        callback = resolve;
      });
    }
  };
  EventEmitter.setDefaultHandler = function (eventName, callback) {
    var handlers = this._defaultHandlers;
    if (!handlers) handlers = this._defaultHandlers = { _disabled_: {} };
    if (handlers[eventName]) {
      var old = handlers[eventName];
      var disabled = handlers._disabled_[eventName];
      if (!disabled) handlers._disabled_[eventName] = disabled = [];
      disabled.push(old);
      var i = disabled.indexOf(callback);
      if (i != -1) disabled.splice(i, 1);
    }
    handlers[eventName] = callback;
  };
  EventEmitter.removeDefaultHandler = function (eventName, callback) {
    var handlers = this._defaultHandlers;
    if (!handlers) return;
    var disabled = handlers._disabled_[eventName];
    if (handlers[eventName] == callback) {
      if (disabled) this.setDefaultHandler(eventName, disabled.pop());
    } else if (disabled) {
      var i = disabled.indexOf(callback);
      if (i != -1) disabled.splice(i, 1);
    }
  };
  EventEmitter.on = EventEmitter.addEventListener = function (
    eventName,
    callback,
    capturing,
  ) {
    this._eventRegistry = this._eventRegistry || {};
    var listeners = this._eventRegistry[eventName];
    if (!listeners) listeners = this._eventRegistry[eventName] = [];
    if (listeners.indexOf(callback) == -1)
      listeners[capturing ? "unshift" : "push"](callback);
    return callback;
  };
  EventEmitter.off =
    EventEmitter.removeListener =
    EventEmitter.removeEventListener =
      function (eventName, callback) {
        this._eventRegistry = this._eventRegistry || {};
        var listeners = this._eventRegistry[eventName];
        if (!listeners) return;
        var index = listeners.indexOf(callback);
        if (index !== -1) listeners.splice(index, 1);
      };
  EventEmitter.removeAllListeners = function (eventName) {
    if (!eventName) this._eventRegistry = this._defaultHandlers = undefined;
    if (this._eventRegistry) this._eventRegistry[eventName] = undefined;
    if (this._defaultHandlers) this._defaultHandlers[eventName] = undefined;
  };
  exports.EventEmitter = EventEmitter;
});

define("ace/lib/report_error", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  exports.reportError = function reportError(msg, data) {
    var e = new Error(msg);
    e["data"] = data;
    if (typeof console == "object" && console.error) console.error(e);
    setTimeout(function () {
      throw e;
    });
  };
});

define("ace/lib/app_config", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/event_emitter",
  "ace/lib/report_error",
], function (require, exports, module) {
  "no use strict";
  var oop = require("./oop");
  var EventEmitter = require("./event_emitter").EventEmitter;
  var reportError = require("./report_error").reportError;
  var optionsProvider = {
    setOptions: function (optList) {
      Object.keys(optList).forEach(function (key) {
        this.setOption(key, optList[key]);
      }, this);
    },
    getOptions: function (optionNames) {
      var result = {};
      if (!optionNames) {
        var options = this.$options;
        optionNames = Object.keys(options).filter(function (key) {
          return !options[key].hidden;
        });
      } else if (!Array.isArray(optionNames)) {
        result = optionNames;
        optionNames = Object.keys(result);
      }
      optionNames.forEach(function (key) {
        result[key] = this.getOption(key);
      }, this);
      return result;
    },
    setOption: function (name, value) {
      if (this["$" + name] === value) return;
      var opt = this.$options[name];
      if (!opt) {
        return warn('misspelled option "' + name + '"');
      }
      if (opt.forwardTo)
        return (
          this[opt.forwardTo] && this[opt.forwardTo].setOption(name, value)
        );
      if (!opt.handlesSet) this["$" + name] = value;
      if (opt && opt.set) opt.set.call(this, value);
    },
    getOption: function (name) {
      var opt = this.$options[name];
      if (!opt) {
        return warn('misspelled option "' + name + '"');
      }
      if (opt.forwardTo)
        return this[opt.forwardTo] && this[opt.forwardTo].getOption(name);
      return opt && opt.get ? opt.get.call(this) : this["$" + name];
    },
  };
  function warn(message) {
    if (typeof console != "undefined" && console.warn)
      console.warn.apply(console, arguments);
  }
  var messages;
  var AppConfig = /** @class */ (function () {
    function AppConfig() {
      this.$defaultOptions = {};
    }
    AppConfig.prototype.defineOptions = function (obj, path, options) {
      if (!obj.$options) this.$defaultOptions[path] = obj.$options = {};
      Object.keys(options).forEach(function (key) {
        var opt = options[key];
        if (typeof opt == "string") opt = { forwardTo: opt };
        opt.name || (opt.name = key);
        obj.$options[opt.name] = opt;
        if ("initialValue" in opt) obj["$" + opt.name] = opt.initialValue;
      });
      oop.implement(obj, optionsProvider);
      return this;
    };
    AppConfig.prototype.resetOptions = function (obj) {
      Object.keys(obj.$options).forEach(function (key) {
        var opt = obj.$options[key];
        if ("value" in opt) obj.setOption(key, opt.value);
      });
    };
    AppConfig.prototype.setDefaultValue = function (path, name, value) {
      if (!path) {
        for (path in this.$defaultOptions)
          if (this.$defaultOptions[path][name]) break;
        if (!this.$defaultOptions[path][name]) return false;
      }
      var opts =
        this.$defaultOptions[path] || (this.$defaultOptions[path] = {});
      if (opts[name]) {
        if (opts.forwardTo) this.setDefaultValue(opts.forwardTo, name, value);
        else opts[name].value = value;
      }
    };
    AppConfig.prototype.setDefaultValues = function (path, optionHash) {
      Object.keys(optionHash).forEach(function (key) {
        this.setDefaultValue(path, key, optionHash[key]);
      }, this);
    };
    AppConfig.prototype.setMessages = function (value) {
      messages = value;
    };
    AppConfig.prototype.nls = function (string, params) {
      if (messages && !messages[string]) {
        warn(
          "No message found for '" +
            string +
            "' in the provided messages, falling back to default English message.",
        );
      }
      var translated = (messages && messages[string]) || string;
      if (params) {
        translated = translated.replace(/\$(\$|[\d]+)/g, function (_, name) {
          if (name == "$") return "$";
          return params[name];
        });
      }
      return translated;
    };
    return AppConfig;
  })();
  AppConfig.prototype.warn = warn;
  AppConfig.prototype.reportError = reportError;
  oop.implement(AppConfig.prototype, EventEmitter);
  exports.AppConfig = AppConfig;
});

define("ace/theme/textmate-css", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  module.exports =
    '.ace-tm .ace_gutter {\n  background: #f0f0f0;\n  color: #333;\n}\n\n.ace-tm .ace_print-margin {\n  width: 1px;\n  background: #e8e8e8;\n}\n\n.ace-tm .ace_fold {\n    background-color: #6B72E6;\n}\n\n.ace-tm {\n  background-color: #FFFFFF;\n  color: black;\n}\n\n.ace-tm .ace_cursor {\n  color: black;\n}\n        \n.ace-tm .ace_invisible {\n  color: rgb(191, 191, 191);\n}\n\n.ace-tm .ace_storage,\n.ace-tm .ace_keyword {\n  color: blue;\n}\n\n.ace-tm .ace_constant {\n  color: rgb(197, 6, 11);\n}\n\n.ace-tm .ace_constant.ace_buildin {\n  color: rgb(88, 72, 246);\n}\n\n.ace-tm .ace_constant.ace_language {\n  color: rgb(88, 92, 246);\n}\n\n.ace-tm .ace_constant.ace_library {\n  color: rgb(6, 150, 14);\n}\n\n.ace-tm .ace_invalid {\n  background-color: rgba(255, 0, 0, 0.1);\n  color: red;\n}\n\n.ace-tm .ace_support.ace_function {\n  color: rgb(60, 76, 114);\n}\n\n.ace-tm .ace_support.ace_constant {\n  color: rgb(6, 150, 14);\n}\n\n.ace-tm .ace_support.ace_type,\n.ace-tm .ace_support.ace_class {\n  color: rgb(109, 121, 222);\n}\n\n.ace-tm .ace_keyword.ace_operator {\n  color: rgb(104, 118, 135);\n}\n\n.ace-tm .ace_string {\n  color: rgb(3, 106, 7);\n}\n\n.ace-tm .ace_comment {\n  color: rgb(76, 136, 107);\n}\n\n.ace-tm .ace_comment.ace_doc {\n  color: rgb(0, 102, 255);\n}\n\n.ace-tm .ace_comment.ace_doc.ace_tag {\n  color: rgb(128, 159, 191);\n}\n\n.ace-tm .ace_constant.ace_numeric {\n  color: rgb(0, 0, 205);\n}\n\n.ace-tm .ace_variable {\n  color: rgb(49, 132, 149);\n}\n\n.ace-tm .ace_xml-pe {\n  color: rgb(104, 104, 91);\n}\n\n.ace-tm .ace_entity.ace_name.ace_function {\n  color: #0000A2;\n}\n\n\n.ace-tm .ace_heading {\n  color: rgb(12, 7, 255);\n}\n\n.ace-tm .ace_list {\n  color:rgb(185, 6, 144);\n}\n\n.ace-tm .ace_meta.ace_tag {\n  color:rgb(0, 22, 142);\n}\n\n.ace-tm .ace_string.ace_regex {\n  color: rgb(255, 0, 0)\n}\n\n.ace-tm .ace_marker-layer .ace_selection {\n  background: rgb(181, 213, 255);\n}\n.ace-tm.ace_multiselect .ace_selection.ace_start {\n  box-shadow: 0 0 3px 0px white;\n}\n.ace-tm .ace_marker-layer .ace_step {\n  background: rgb(252, 255, 0);\n}\n\n.ace-tm .ace_marker-layer .ace_stack {\n  background: rgb(164, 229, 101);\n}\n\n.ace-tm .ace_marker-layer .ace_bracket {\n  margin: -1px 0 0 -1px;\n  border: 1px solid rgb(192, 192, 192);\n}\n\n.ace-tm .ace_marker-layer .ace_active-line {\n  background: rgba(0, 0, 0, 0.07);\n}\n\n.ace-tm .ace_gutter-active-line {\n    background-color : #dcdcdc;\n}\n\n.ace-tm .ace_marker-layer .ace_selected-word {\n  background: rgb(250, 250, 255);\n  border: 1px solid rgb(200, 200, 250);\n}\n\n.ace-tm .ace_indent-guide {\n  background: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAACCAYAAACZgbYnAAAAE0lEQVQImWP4////f4bLly//BwAmVgd1/w11/gAAAABJRU5ErkJggg==") right repeat-y;\n}\n\n.ace-tm .ace_indent-guide-active {\n  background: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAACCAYAAACZgbYnAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAIGNIUk0AAHolAACAgwAA+f8AAIDpAAB1MAAA6mAAADqYAAAXb5JfxUYAAAAZSURBVHjaYvj///9/hivKyv8BAAAA//8DACLqBhbvk+/eAAAAAElFTkSuQmCC") right repeat-y;\n}\n';
});

define("ace/theme/textmate", [
  "require",
  "exports",
  "module",
  "ace/theme/textmate-css",
  "ace/lib/dom",
], function (require, exports, module) {
  "use strict";
  exports.isDark = false;
  exports.cssClass = "ace-tm";
  exports.cssText = require("./textmate-css");
  exports.$id = "ace/theme/textmate";
  var dom = require("../lib/dom");
  dom.importCssString(exports.cssText, exports.cssClass, false);
});

define("ace/config", [
  "require",
  "exports",
  "module",
  "ace/lib/lang",
  "ace/lib/net",
  "ace/lib/dom",
  "ace/lib/app_config",
  "ace/theme/textmate",
], function (require, exports, module) {
  "no use strict";
  var lang = require("./lib/lang");
  var net = require("./lib/net");
  var dom = require("./lib/dom");
  var AppConfig = require("./lib/app_config").AppConfig;
  module.exports = exports = new AppConfig();
  var options = {
    packaged: false,
    workerPath: null,
    modePath: null,
    themePath: null,
    basePath: "",
    suffix: ".js",
    $moduleUrls: {},
    loadWorkerFromBlob: true,
    sharedPopups: false,
    useStrictCSP: null,
  };
  exports.get = function (key) {
    if (!options.hasOwnProperty(key))
      throw new Error("Unknown config key: " + key);
    return options[key];
  };
  exports.set = function (key, value) {
    if (options.hasOwnProperty(key)) options[key] = value;
    else if (this.setDefaultValue("", key, value) == false)
      throw new Error("Unknown config key: " + key);
    if (key == "useStrictCSP") dom.useStrictCSP(value);
  };
  exports.all = function () {
    return lang.copyObject(options);
  };
  exports.$modes = {};
  exports.moduleUrl = function (name, component) {
    if (options.$moduleUrls[name]) return options.$moduleUrls[name];
    var parts = name.split("/");
    component = component || parts[parts.length - 2] || "";
    var sep = component == "snippets" ? "/" : "-";
    var base = parts[parts.length - 1];
    if (component == "worker" && sep == "-") {
      var re = new RegExp(
        "^" + component + "[\\-_]|[\\-_]" + component + "$",
        "g",
      );
      base = base.replace(re, "");
    }
    if ((!base || base == component) && parts.length > 1)
      base = parts[parts.length - 2];
    var path = options[component + "Path"];
    if (path == null) {
      path = options.basePath;
    } else if (sep == "/") {
      component = sep = "";
    }
    if (path && path.slice(-1) != "/") path += "/";
    return path + component + sep + base + this.get("suffix");
  };
  exports.setModuleUrl = function (name, subst) {
    return (options.$moduleUrls[name] = subst);
  };
  var loader = function (moduleName, cb) {
    if (
      moduleName === "ace/theme/textmate" ||
      moduleName === "./theme/textmate"
    )
      return cb(null, require("./theme/textmate"));
    if (customLoader) return customLoader(moduleName, cb);
    console.error("loader is not configured");
  };
  var customLoader;
  exports.setLoader = function (cb) {
    customLoader = cb;
  };
  exports.dynamicModules = Object.create(null);
  exports.$loading = {};
  exports.$loaded = {};
  exports.loadModule = function (moduleId, onLoad) {
    var loadedModule;
    if (Array.isArray(moduleId)) {
      var moduleType = moduleId[0];
      var moduleName = moduleId[1];
    } else if (typeof moduleId == "string") {
      var moduleName = moduleId;
    }
    var load = function (module) {
      if (module && !exports.$loading[moduleName])
        return onLoad && onLoad(module);
      if (!exports.$loading[moduleName]) exports.$loading[moduleName] = [];
      exports.$loading[moduleName].push(onLoad);
      if (exports.$loading[moduleName].length > 1) return;
      var afterLoad = function () {
        loader(moduleName, function (err, module) {
          if (module) exports.$loaded[moduleName] = module;
          exports._emit("load.module", { name: moduleName, module: module });
          var listeners = exports.$loading[moduleName];
          exports.$loading[moduleName] = null;
          listeners.forEach(function (onLoad) {
            onLoad && onLoad(module);
          });
        });
      };
      if (!exports.get("packaged")) return afterLoad();
      net.loadScript(exports.moduleUrl(moduleName, moduleType), afterLoad);
      reportErrorIfPathIsNotConfigured();
    };
    if (exports.dynamicModules[moduleName]) {
      exports.dynamicModules[moduleName]().then(function (module) {
        if (module.default) {
          load(module.default);
        } else {
          load(module);
        }
      });
    } else {
      try {
        loadedModule = this.$require(moduleName);
      } catch (e) {}
      load(loadedModule || exports.$loaded[moduleName]);
    }
  };
  exports.$require = function (moduleName) {
    if (typeof module["require"] == "function") {
      var req = "require";
      return module[req](moduleName);
    }
  };
  exports.setModuleLoader = function (moduleName, onLoad) {
    exports.dynamicModules[moduleName] = onLoad;
  };
  var reportErrorIfPathIsNotConfigured = function () {
    if (
      !options.basePath &&
      !options.workerPath &&
      !options.modePath &&
      !options.themePath &&
      !Object.keys(options.$moduleUrls).length
    ) {
      console.error(
        "Unable to infer path to ace from script src,",
        "use ace.config.set('basePath', 'path') to enable dynamic loading of modes and themes",
        "or with webpack use ace/webpack-resolver",
      );
      reportErrorIfPathIsNotConfigured = function () {};
    }
  };
  exports.version = "1.32.3";
});

define("ace/loader_build", [
  "require",
  "exports",
  "module",
  "ace/lib/fixoldbrowsers",
  "ace/config",
], function (require, exports, module) {
  "use strict";

  require("./lib/fixoldbrowsers");
  var config = require("./config");
  config.setLoader(function (moduleName, cb) {
    require([moduleName], function (module) {
      cb(null, module);
    });
  });

  var global = (function () {
    return this || (typeof window != "undefined" && window);
  })();

  module.exports = function (ace) {
    config.init = init;
    config.$require = require;
    ace.require = require;

    if (typeof define === "function") ace.define = define;
  };
  init(true);
  function init(packaged) {
    if (!global || !global.document) return;

    config.set(
      "packaged",
      packaged ||
        require.packaged ||
        module.packaged ||
        (global.define && define.packaged),
    );

    var scriptOptions = {};
    var scriptUrl = "";
    var currentScript = document.currentScript || document._currentScript; // native or polyfill
    var currentDocument =
      (currentScript && currentScript.ownerDocument) || document;

    if (currentScript && currentScript.src) {
      scriptUrl =
        currentScript.src.split(/[?#]/)[0].split("/").slice(0, -1).join("/") ||
        "";
    }

    var scripts = currentDocument.getElementsByTagName("script");
    for (var i = 0; i < scripts.length; i++) {
      var script = scripts[i];

      var src = script.src || script.getAttribute("src");
      if (!src) continue;

      var attributes = script.attributes;
      for (var j = 0, l = attributes.length; j < l; j++) {
        var attr = attributes[j];
        if (attr.name.indexOf("data-ace-") === 0) {
          scriptOptions[deHyphenate(attr.name.replace(/^data-ace-/, ""))] =
            attr.value;
        }
      }

      var m = src.match(/^(.*)\/ace([\-.]\w+)?\.js(\?|$)/);
      if (m) scriptUrl = m[1];
    }

    if (scriptUrl) {
      scriptOptions.base = scriptOptions.base || scriptUrl;
      scriptOptions.packaged = true;
    }

    scriptOptions.basePath = scriptOptions.base;
    scriptOptions.workerPath = scriptOptions.workerPath || scriptOptions.base;
    scriptOptions.modePath = scriptOptions.modePath || scriptOptions.base;
    scriptOptions.themePath = scriptOptions.themePath || scriptOptions.base;
    delete scriptOptions.base;

    for (var key in scriptOptions)
      if (typeof scriptOptions[key] !== "undefined")
        config.set(key, scriptOptions[key]);
  }

  function deHyphenate(str) {
    return str.replace(/-(.)/g, function (m, m1) {
      return m1.toUpperCase();
    });
  }
});

define("ace/range", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  "use strict";
  var Range = /** @class */ (function () {
    function Range(startRow, startColumn, endRow, endColumn) {
      this.start = {
        row: startRow,
        column: startColumn,
      };
      this.end = {
        row: endRow,
        column: endColumn,
      };
    }
    Range.prototype.isEqual = function (range) {
      return (
        this.start.row === range.start.row &&
        this.end.row === range.end.row &&
        this.start.column === range.start.column &&
        this.end.column === range.end.column
      );
    };
    Range.prototype.toString = function () {
      return (
        "Range: [" +
        this.start.row +
        "/" +
        this.start.column +
        "] -> [" +
        this.end.row +
        "/" +
        this.end.column +
        "]"
      );
    };
    Range.prototype.contains = function (row, column) {
      return this.compare(row, column) == 0;
    };
    Range.prototype.compareRange = function (range) {
      var cmp,
        end = range.end,
        start = range.start;
      cmp = this.compare(end.row, end.column);
      if (cmp == 1) {
        cmp = this.compare(start.row, start.column);
        if (cmp == 1) {
          return 2;
        } else if (cmp == 0) {
          return 1;
        } else {
          return 0;
        }
      } else if (cmp == -1) {
        return -2;
      } else {
        cmp = this.compare(start.row, start.column);
        if (cmp == -1) {
          return -1;
        } else if (cmp == 1) {
          return 42;
        } else {
          return 0;
        }
      }
    };
    Range.prototype.comparePoint = function (p) {
      return this.compare(p.row, p.column);
    };
    Range.prototype.containsRange = function (range) {
      return (
        this.comparePoint(range.start) == 0 && this.comparePoint(range.end) == 0
      );
    };
    Range.prototype.intersects = function (range) {
      var cmp = this.compareRange(range);
      return cmp == -1 || cmp == 0 || cmp == 1;
    };
    Range.prototype.isEnd = function (row, column) {
      return this.end.row == row && this.end.column == column;
    };
    Range.prototype.isStart = function (row, column) {
      return this.start.row == row && this.start.column == column;
    };
    Range.prototype.setStart = function (row, column) {
      if (typeof row == "object") {
        this.start.column = row.column;
        this.start.row = row.row;
      } else {
        this.start.row = row;
        this.start.column = column;
      }
    };
    Range.prototype.setEnd = function (row, column) {
      if (typeof row == "object") {
        this.end.column = row.column;
        this.end.row = row.row;
      } else {
        this.end.row = row;
        this.end.column = column;
      }
    };
    Range.prototype.inside = function (row, column) {
      if (this.compare(row, column) == 0) {
        if (this.isEnd(row, column) || this.isStart(row, column)) {
          return false;
        } else {
          return true;
        }
      }
      return false;
    };
    Range.prototype.insideStart = function (row, column) {
      if (this.compare(row, column) == 0) {
        if (this.isEnd(row, column)) {
          return false;
        } else {
          return true;
        }
      }
      return false;
    };
    Range.prototype.insideEnd = function (row, column) {
      if (this.compare(row, column) == 0) {
        if (this.isStart(row, column)) {
          return false;
        } else {
          return true;
        }
      }
      return false;
    };
    Range.prototype.compare = function (row, column) {
      if (!this.isMultiLine()) {
        if (row === this.start.row) {
          return column < this.start.column
            ? -1
            : column > this.end.column
              ? 1
              : 0;
        }
      }
      if (row < this.start.row) return -1;
      if (row > this.end.row) return 1;
      if (this.start.row === row) return column >= this.start.column ? 0 : -1;
      if (this.end.row === row) return column <= this.end.column ? 0 : 1;
      return 0;
    };
    Range.prototype.compareStart = function (row, column) {
      if (this.start.row == row && this.start.column == column) {
        return -1;
      } else {
        return this.compare(row, column);
      }
    };
    Range.prototype.compareEnd = function (row, column) {
      if (this.end.row == row && this.end.column == column) {
        return 1;
      } else {
        return this.compare(row, column);
      }
    };
    Range.prototype.compareInside = function (row, column) {
      if (this.end.row == row && this.end.column == column) {
        return 1;
      } else if (this.start.row == row && this.start.column == column) {
        return -1;
      } else {
        return this.compare(row, column);
      }
    };
    Range.prototype.clipRows = function (firstRow, lastRow) {
      if (this.end.row > lastRow) var end = { row: lastRow + 1, column: 0 };
      else if (this.end.row < firstRow) var end = { row: firstRow, column: 0 };
      if (this.start.row > lastRow) var start = { row: lastRow + 1, column: 0 };
      else if (this.start.row < firstRow)
        var start = { row: firstRow, column: 0 };
      return Range.fromPoints(start || this.start, end || this.end);
    };
    Range.prototype.extend = function (row, column) {
      var cmp = this.compare(row, column);
      if (cmp == 0) return this;
      else if (cmp == -1) var start = { row: row, column: column };
      else var end = { row: row, column: column };
      return Range.fromPoints(start || this.start, end || this.end);
    };
    Range.prototype.isEmpty = function () {
      return (
        this.start.row === this.end.row && this.start.column === this.end.column
      );
    };
    Range.prototype.isMultiLine = function () {
      return this.start.row !== this.end.row;
    };
    Range.prototype.clone = function () {
      return Range.fromPoints(this.start, this.end);
    };
    Range.prototype.collapseRows = function () {
      if (this.end.column == 0)
        return new Range(
          this.start.row,
          0,
          Math.max(this.start.row, this.end.row - 1),
          0,
        );
      else return new Range(this.start.row, 0, this.end.row, 0);
    };
    Range.prototype.toScreenRange = function (session) {
      var screenPosStart = session.documentToScreenPosition(this.start);
      var screenPosEnd = session.documentToScreenPosition(this.end);
      return new Range(
        screenPosStart.row,
        screenPosStart.column,
        screenPosEnd.row,
        screenPosEnd.column,
      );
    };
    Range.prototype.moveBy = function (row, column) {
      this.start.row += row;
      this.start.column += column;
      this.end.row += row;
      this.end.column += column;
    };
    return Range;
  })();
  Range.fromPoints = function (start, end) {
    return new Range(start.row, start.column, end.row, end.column);
  };
  Range.comparePoints = function (p1, p2) {
    return p1.row - p2.row || p1.column - p2.column;
  };
  exports.Range = Range;
});

define("ace/lib/keys", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
], function (require, exports, module) {
  /*! @license
    ==========================================================================
    SproutCore -- JavaScript Application Framework
    copyright 2006-2009, Sprout Systems Inc., Apple Inc. and contributors.
    
    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:
    
    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.
    
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.
    
    SproutCore and the SproutCore logo are trademarks of Sprout Systems, Inc.
    
    For more information about SproutCore, visit http://www.sproutcore.com
    
    
    ==========================================================================
    @license */
  "use strict";
  var oop = require("./oop");
  var Keys = (function () {
    var ret = {
      MODIFIER_KEYS: {
        16: "Shift",
        17: "Ctrl",
        18: "Alt",
        224: "Meta",
        91: "MetaLeft",
        92: "MetaRight",
        93: "ContextMenu",
      },
      KEY_MODS: {
        ctrl: 1,
        alt: 2,
        option: 2,
        shift: 4,
        super: 8,
        meta: 8,
        command: 8,
        cmd: 8,
        control: 1,
      },
      FUNCTION_KEYS: {
        8: "Backspace",
        9: "Tab",
        13: "Return",
        19: "Pause",
        27: "Esc",
        32: "Space",
        33: "PageUp",
        34: "PageDown",
        35: "End",
        36: "Home",
        37: "Left",
        38: "Up",
        39: "Right",
        40: "Down",
        44: "Print",
        45: "Insert",
        46: "Delete",
        96: "Numpad0",
        97: "Numpad1",
        98: "Numpad2",
        99: "Numpad3",
        100: "Numpad4",
        101: "Numpad5",
        102: "Numpad6",
        103: "Numpad7",
        104: "Numpad8",
        105: "Numpad9",
        "-13": "NumpadEnter",
        112: "F1",
        113: "F2",
        114: "F3",
        115: "F4",
        116: "F5",
        117: "F6",
        118: "F7",
        119: "F8",
        120: "F9",
        121: "F10",
        122: "F11",
        123: "F12",
        144: "Numlock",
        145: "Scrolllock",
      },
      PRINTABLE_KEYS: {
        32: " ",
        48: "0",
        49: "1",
        50: "2",
        51: "3",
        52: "4",
        53: "5",
        54: "6",
        55: "7",
        56: "8",
        57: "9",
        59: ";",
        61: "=",
        65: "a",
        66: "b",
        67: "c",
        68: "d",
        69: "e",
        70: "f",
        71: "g",
        72: "h",
        73: "i",
        74: "j",
        75: "k",
        76: "l",
        77: "m",
        78: "n",
        79: "o",
        80: "p",
        81: "q",
        82: "r",
        83: "s",
        84: "t",
        85: "u",
        86: "v",
        87: "w",
        88: "x",
        89: "y",
        90: "z",
        107: "+",
        109: "-",
        110: ".",
        186: ";",
        187: "=",
        188: ",",
        189: "-",
        190: ".",
        191: "/",
        192: "`",
        219: "[",
        220: "\\",
        221: "]",
        222: "'",
        111: "/",
        106: "*",
      },
    };
    ret.PRINTABLE_KEYS[173] = "-";
    var name, i;
    for (i in ret.FUNCTION_KEYS) {
      name = ret.FUNCTION_KEYS[i].toLowerCase();
      ret[name] = parseInt(i, 10);
    }
    for (i in ret.PRINTABLE_KEYS) {
      name = ret.PRINTABLE_KEYS[i].toLowerCase();
      ret[name] = parseInt(i, 10);
    }
    oop.mixin(ret, ret.MODIFIER_KEYS);
    oop.mixin(ret, ret.PRINTABLE_KEYS);
    oop.mixin(ret, ret.FUNCTION_KEYS);
    ret.enter = ret["return"];
    ret.escape = ret.esc;
    ret.del = ret["delete"];
    (function () {
      var mods = ["cmd", "ctrl", "alt", "shift"];
      for (var i = Math.pow(2, mods.length); i--; ) {
        ret.KEY_MODS[i] =
          mods
            .filter(function (x) {
              return i & ret.KEY_MODS[x];
            })
            .join("-") + "-";
      }
    })();
    ret.KEY_MODS[0] = "";
    ret.KEY_MODS[-1] = "input-";
    return ret;
  })();
  oop.mixin(exports, Keys);
  exports.default = exports;
  exports.keyCodeToString = function (keyCode) {
    var keyString = Keys[keyCode];
    if (typeof keyString != "string") keyString = String.fromCharCode(keyCode);
    return keyString.toLowerCase();
  };
});

define("ace/lib/event", [
  "require",
  "exports",
  "module",
  "ace/lib/keys",
  "ace/lib/useragent",
], function (require, exports, module) {
  "use strict";
  var keys = require("./keys");
  var useragent = require("./useragent");
  var pressedKeys = null;
  var ts = 0;
  var activeListenerOptions;
  function detectListenerOptionsSupport() {
    activeListenerOptions = false;
    try {
      document.createComment("").addEventListener("test", function () {}, {
        get passive() {
          activeListenerOptions = { passive: false };
          return true;
        },
      });
    } catch (e) {}
  }
  function getListenerOptions() {
    if (activeListenerOptions == undefined) detectListenerOptionsSupport();
    return activeListenerOptions;
  }
  function EventListener(elem, type, callback) {
    this.elem = elem;
    this.type = type;
    this.callback = callback;
  }
  EventListener.prototype.destroy = function () {
    removeListener(this.elem, this.type, this.callback);
    this.elem = this.type = this.callback = undefined;
  };
  var addListener = (exports.addListener = function (
    elem,
    type,
    callback,
    /**@type{any?}*/ destroyer,
  ) {
    elem.addEventListener(type, callback, getListenerOptions());
    if (destroyer)
      destroyer.$toDestroy.push(new EventListener(elem, type, callback));
  });
  var removeListener = (exports.removeListener = function (
    elem,
    type,
    callback,
  ) {
    elem.removeEventListener(type, callback, getListenerOptions());
  });
  exports.stopEvent = function (e) {
    exports.stopPropagation(e);
    exports.preventDefault(e);
    return false;
  };
  exports.stopPropagation = function (e) {
    if (e.stopPropagation) e.stopPropagation();
  };
  exports.preventDefault = function (e) {
    if (e.preventDefault) e.preventDefault();
  };
  exports.getButton = function (e) {
    if (e.type == "dblclick") return 0;
    if (
      e.type == "contextmenu" ||
      (useragent.isMac && e.ctrlKey && !e.altKey && !e.shiftKey)
    )
      return 2;
    return e.button;
  };
  exports.capture = function (el, eventHandler, releaseCaptureHandler) {
    var ownerDocument = (el && el.ownerDocument) || document;
    function onMouseUp(e) {
      eventHandler && eventHandler(e);
      releaseCaptureHandler && releaseCaptureHandler(e);
      removeListener(ownerDocument, "mousemove", eventHandler);
      removeListener(ownerDocument, "mouseup", onMouseUp);
      removeListener(ownerDocument, "dragstart", onMouseUp);
    }
    addListener(ownerDocument, "mousemove", eventHandler);
    addListener(ownerDocument, "mouseup", onMouseUp);
    addListener(ownerDocument, "dragstart", onMouseUp);
    return onMouseUp;
  };
  exports.addMouseWheelListener = function (el, callback, destroyer) {
    addListener(
      el,
      "wheel",
      function (e) {
        var factor = 0.15;
        var deltaX = e.deltaX || 0;
        var deltaY = e.deltaY || 0;
        switch (e.deltaMode) {
          case e.DOM_DELTA_PIXEL:
            e.wheelX = deltaX * factor;
            e.wheelY = deltaY * factor;
            break;
          case e.DOM_DELTA_LINE:
            var linePixels = 15;
            e.wheelX = deltaX * linePixels;
            e.wheelY = deltaY * linePixels;
            break;
          case e.DOM_DELTA_PAGE:
            var pagePixels = 150;
            e.wheelX = deltaX * pagePixels;
            e.wheelY = deltaY * pagePixels;
            break;
        }
        callback(e);
      },
      destroyer,
    );
  };
  exports.addMultiMouseDownListener = function (
    elements,
    timeouts,
    eventHandler,
    callbackName,
    destroyer,
  ) {
    var clicks = 0;
    var startX, startY, timer;
    var eventNames = {
      2: "dblclick",
      3: "tripleclick",
      4: "quadclick",
    };
    function onMousedown(e) {
      if (exports.getButton(e) !== 0) {
        clicks = 0;
      } else if (e.detail > 1) {
        clicks++;
        if (clicks > 4) clicks = 1;
      } else {
        clicks = 1;
      }
      if (useragent.isIE) {
        var isNewClick =
          Math.abs(e.clientX - startX) > 5 || Math.abs(e.clientY - startY) > 5;
        if (!timer || isNewClick) clicks = 1;
        if (timer) clearTimeout(timer);
        timer = setTimeout(
          function () {
            timer = null;
          },
          timeouts[clicks - 1] || 600,
        );
        if (clicks == 1) {
          startX = e.clientX;
          startY = e.clientY;
        }
      }
      e._clicks = clicks;
      eventHandler[callbackName]("mousedown", e);
      if (clicks > 4) clicks = 0;
      else if (clicks > 1)
        return eventHandler[callbackName](eventNames[clicks], e);
    }
    if (!Array.isArray(elements)) elements = [elements];
    elements.forEach(function (el) {
      addListener(el, "mousedown", onMousedown, destroyer);
    });
  };
  var getModifierHash = function (e) {
    return (
      0 |
      (e.ctrlKey ? 1 : 0) |
      (e.altKey ? 2 : 0) |
      (e.shiftKey ? 4 : 0) |
      (e.metaKey ? 8 : 0)
    );
  };
  exports.getModifierString = function (e) {
    return keys.KEY_MODS[getModifierHash(e)];
  };
  function normalizeCommandKeys(callback, e, keyCode) {
    var hashId = getModifierHash(e);
    if (!useragent.isMac && pressedKeys) {
      if (
        e.getModifierState &&
        (e.getModifierState("OS") || e.getModifierState("Win"))
      )
        hashId |= 8;
      if (pressedKeys.altGr) {
        if ((3 & hashId) != 3) pressedKeys.altGr = 0;
        else return;
      }
      if (keyCode === 18 || keyCode === 17) {
        var location = "location" in e ? e.location : e.keyLocation;
        if (keyCode === 17 && location === 1) {
          if (pressedKeys[keyCode] == 1) ts = e.timeStamp;
        } else if (keyCode === 18 && hashId === 3 && location === 2) {
          var dt = e.timeStamp - ts;
          if (dt < 50) pressedKeys.altGr = true;
        }
      }
    }
    if (keyCode in keys.MODIFIER_KEYS) {
      keyCode = -1;
    }
    if (!hashId && keyCode === 13) {
      var location = "location" in e ? e.location : e.keyLocation;
      if (location === 3) {
        callback(e, hashId, -keyCode);
        if (e.defaultPrevented) return;
      }
    }
    if (useragent.isChromeOS && hashId & 8) {
      callback(e, hashId, keyCode);
      if (e.defaultPrevented) return;
      else hashId &= ~8;
    }
    if (
      !hashId &&
      !(keyCode in keys.FUNCTION_KEYS) &&
      !(keyCode in keys.PRINTABLE_KEYS)
    ) {
      return false;
    }
    return callback(e, hashId, keyCode);
  }
  exports.addCommandKeyListener = function (el, callback, destroyer) {
    var lastDefaultPrevented = null;
    addListener(
      el,
      "keydown",
      function (e) {
        pressedKeys[e.keyCode] = (pressedKeys[e.keyCode] || 0) + 1;
        var result = normalizeCommandKeys(callback, e, e.keyCode);
        lastDefaultPrevented = e.defaultPrevented;
        return result;
      },
      destroyer,
    );
    addListener(
      el,
      "keypress",
      function (e) {
        if (
          lastDefaultPrevented &&
          (e.ctrlKey || e.altKey || e.shiftKey || e.metaKey)
        ) {
          exports.stopEvent(e);
          lastDefaultPrevented = null;
        }
      },
      destroyer,
    );
    addListener(
      el,
      "keyup",
      function (e) {
        pressedKeys[e.keyCode] = null;
      },
      destroyer,
    );
    if (!pressedKeys) {
      resetPressedKeys();
      addListener(window, "focus", resetPressedKeys);
    }
  };
  function resetPressedKeys() {
    pressedKeys = Object.create(null);
  }
  if (typeof window == "object" && window.postMessage && !useragent.isOldIE) {
    var postMessageId = 1;
    exports.nextTick = function (callback, win) {
      win = win || window;
      var messageName = "zero-timeout-message-" + postMessageId++;
      var listener = function (e) {
        if (e.data == messageName) {
          exports.stopPropagation(e);
          removeListener(win, "message", listener);
          callback();
        }
      };
      addListener(win, "message", listener);
      win.postMessage(messageName, "*");
    };
  }
  exports.$idleBlocked = false;
  exports.onIdle = function (cb, timeout) {
    return setTimeout(function handler() {
      if (!exports.$idleBlocked) {
        cb();
      } else {
        setTimeout(handler, 100);
      }
    }, timeout);
  };
  exports.$idleBlockId = null;
  exports.blockIdle = function (delay) {
    if (exports.$idleBlockId) clearTimeout(exports.$idleBlockId);
    exports.$idleBlocked = true;
    exports.$idleBlockId = setTimeout(function () {
      exports.$idleBlocked = false;
    }, delay || 100);
  };
  exports.nextFrame =
    typeof window == "object" &&
    (window.requestAnimationFrame ||
      window["mozRequestAnimationFrame"] ||
      window["webkitRequestAnimationFrame"] ||
      window["msRequestAnimationFrame"] ||
      window["oRequestAnimationFrame"]);
  if (exports.nextFrame) exports.nextFrame = exports.nextFrame.bind(window);
  else
    exports.nextFrame = function (callback) {
      setTimeout(callback, 17);
    };
});

define("ace/clipboard", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  "use strict";
  var $cancelT;
  module.exports = {
    lineMode: false,
    pasteCancelled: function () {
      if ($cancelT && $cancelT > Date.now() - 50) return true;
      return ($cancelT = false);
    },
    cancel: function () {
      $cancelT = Date.now();
    },
  };
});

define("ace/keyboard/textinput", [
  "require",
  "exports",
  "module",
  "ace/lib/event",
  "ace/config",
  "ace/lib/useragent",
  "ace/lib/dom",
  "ace/lib/lang",
  "ace/clipboard",
  "ace/lib/keys",
], function (require, exports, module) {
  "use strict";
  var event = require("../lib/event");
  var nls = require("../config").nls;
  var useragent = require("../lib/useragent");
  var dom = require("../lib/dom");
  var lang = require("../lib/lang");
  var clipboard = require("../clipboard");
  var BROKEN_SETDATA = useragent.isChrome < 18;
  var USE_IE_MIME_TYPE = useragent.isIE;
  var HAS_FOCUS_ARGS = useragent.isChrome > 63;
  var MAX_LINE_LENGTH = 400;
  var KEYS = require("../lib/keys");
  var MODS = KEYS.KEY_MODS;
  var isIOS = useragent.isIOS;
  var valueResetRegex = isIOS ? /\s/ : /\n/;
  var isMobile = useragent.isMobile;
  var TextInput;
  TextInput = function (parentNode, host) {
    var text = dom.createElement("textarea");
    text.className = "ace_text-input";
    text.setAttribute("wrap", "off");
    text.setAttribute("autocorrect", "off");
    text.setAttribute("autocapitalize", "off");
    text.setAttribute("spellcheck", "false");
    text.style.opacity = "0";
    parentNode.insertBefore(text, parentNode.firstChild);
    var copied = false;
    var pasted = false;
    var inComposition = false;
    var sendingText = false;
    var tempStyle = "";
    if (!isMobile) text.style.fontSize = "1px";
    var commandMode = false;
    var ignoreFocusEvents = false;
    var lastValue = "";
    var lastSelectionStart = 0;
    var lastSelectionEnd = 0;
    var lastRestoreEnd = 0;
    var rowStart = Number.MAX_SAFE_INTEGER;
    var rowEnd = Number.MIN_SAFE_INTEGER;
    var numberOfExtraLines = 0;
    try {
      var isFocused = document.activeElement === text;
    } catch (e) {}
    this.setNumberOfExtraLines = function (number) {
      rowStart = Number.MAX_SAFE_INTEGER;
      rowEnd = Number.MIN_SAFE_INTEGER;
      if (number < 0) {
        numberOfExtraLines = 0;
        return;
      }
      numberOfExtraLines = number;
    };
    this.setAriaOptions = function (options) {
      if (options.activeDescendant) {
        text.setAttribute("aria-haspopup", "true");
        text.setAttribute(
          "aria-autocomplete",
          options.inline ? "both" : "list",
        );
        text.setAttribute("aria-activedescendant", options.activeDescendant);
      } else {
        text.setAttribute("aria-haspopup", "false");
        text.setAttribute("aria-autocomplete", "both");
        text.removeAttribute("aria-activedescendant");
      }
      if (options.role) {
        text.setAttribute("role", options.role);
      }
      if (options.setLabel) {
        text.setAttribute("aria-roledescription", nls("editor"));
        if (host.session) {
          var row = host.session.selection.cursor.row;
          text.setAttribute("aria-label", nls("Cursor at row $0", [row + 1]));
        }
      }
    };
    this.setAriaOptions({ role: "textbox" });
    event.addListener(
      text,
      "blur",
      function (e) {
        if (ignoreFocusEvents) return;
        host.onBlur(e);
        isFocused = false;
      },
      host,
    );
    event.addListener(
      text,
      "focus",
      function (e) {
        if (ignoreFocusEvents) return;
        isFocused = true;
        if (useragent.isEdge) {
          try {
            if (!document.hasFocus()) return;
          } catch (e) {}
        }
        host.onFocus(e);
        if (useragent.isEdge) setTimeout(resetSelection);
        else resetSelection();
      },
      host,
    );
    this.$focusScroll = false;
    this.focus = function () {
      this.setAriaOptions({
        setLabel: host.renderer.enableKeyboardAccessibility,
      });
      if (tempStyle || HAS_FOCUS_ARGS || this.$focusScroll == "browser")
        return text.focus({ preventScroll: true });
      var top = text.style.top;
      text.style.position = "fixed";
      text.style.top = "0px";
      try {
        var isTransformed = text.getBoundingClientRect().top != 0;
      } catch (e) {
        return;
      }
      var ancestors = [];
      if (isTransformed) {
        var t = text.parentElement;
        while (t && t.nodeType == 1) {
          ancestors.push(t);
          t.setAttribute("ace_nocontext", "true");
          if (!t.parentElement && t.getRootNode) t = t.getRootNode()["host"];
          else t = t.parentElement;
        }
      }
      text.focus({ preventScroll: true });
      if (isTransformed) {
        ancestors.forEach(function (p) {
          p.removeAttribute("ace_nocontext");
        });
      }
      setTimeout(function () {
        text.style.position = "";
        if (text.style.top == "0px") text.style.top = top;
      }, 0);
    };
    this.blur = function () {
      text.blur();
    };
    this.isFocused = function () {
      return isFocused;
    };
    host.on("beforeEndOperation", function () {
      var curOp = host.curOp;
      var commandName = curOp && curOp.command && curOp.command.name;
      if (commandName == "insertstring") return;
      var isUserAction =
        commandName && (curOp.docChanged || curOp.selectionChanged);
      if (inComposition && isUserAction) {
        lastValue = text.value = "";
        onCompositionEnd();
      }
      resetSelection();
    });
    var positionToSelection = function (row, column) {
      var selection = column;
      for (
        var i = 1;
        i <= row - rowStart && i < 2 * numberOfExtraLines + 1;
        i++
      ) {
        selection += host.session.getLine(row - i).length + 1;
      }
      return selection;
    };
    var resetSelection = isIOS
      ? function (value) {
          if (!isFocused || (copied && !value) || sendingText) return;
          if (!value) value = "";
          var newValue = "\n ab" + value + "cde fg\n";
          if (newValue != text.value) text.value = lastValue = newValue;
          var selectionStart = 4;
          var selectionEnd =
            4 + (value.length || (host.selection.isEmpty() ? 0 : 1));
          if (
            lastSelectionStart != selectionStart ||
            lastSelectionEnd != selectionEnd
          ) {
            text.setSelectionRange(selectionStart, selectionEnd);
          }
          lastSelectionStart = selectionStart;
          lastSelectionEnd = selectionEnd;
        }
      : function () {
          if (inComposition || sendingText) return;
          if (!isFocused && !afterContextMenu) return;
          inComposition = true;
          var selectionStart = 0;
          var selectionEnd = 0;
          var line = "";
          if (host.session) {
            var selection = host.selection;
            var range = selection.getRange();
            var row = selection.cursor.row;
            if (row === rowEnd + 1) {
              rowStart = rowEnd + 1;
              rowEnd = rowStart + 2 * numberOfExtraLines;
            } else if (row === rowStart - 1) {
              rowEnd = rowStart - 1;
              rowStart = rowEnd - 2 * numberOfExtraLines;
            } else if (row < rowStart - 1 || row > rowEnd + 1) {
              rowStart =
                row > numberOfExtraLines ? row - numberOfExtraLines : 0;
              rowEnd =
                row > numberOfExtraLines
                  ? row + numberOfExtraLines
                  : 2 * numberOfExtraLines;
            }
            var lines = [];
            for (var i = rowStart; i <= rowEnd; i++) {
              lines.push(host.session.getLine(i));
            }
            line = lines.join("\n");
            selectionStart = positionToSelection(
              range.start.row,
              range.start.column,
            );
            selectionEnd = positionToSelection(range.end.row, range.end.column);
            if (range.start.row < rowStart) {
              var prevLine = host.session.getLine(rowStart - 1);
              selectionStart =
                range.start.row < rowStart - 1 ? 0 : selectionStart;
              selectionEnd += prevLine.length + 1;
              line = prevLine + "\n" + line;
            } else if (range.end.row > rowEnd) {
              var nextLine = host.session.getLine(rowEnd + 1);
              selectionEnd =
                range.end.row > rowEnd + 1 ? nextLine.length : range.end.column;
              selectionEnd += line.length + 1;
              line = line + "\n" + nextLine;
            } else if (isMobile && row > 0) {
              line = "\n" + line;
              selectionEnd += 1;
              selectionStart += 1;
            }
            if (line.length > MAX_LINE_LENGTH) {
              if (
                selectionStart < MAX_LINE_LENGTH &&
                selectionEnd < MAX_LINE_LENGTH
              ) {
                line = line.slice(0, MAX_LINE_LENGTH);
              } else {
                line = "\n";
                if (selectionStart == selectionEnd) {
                  selectionStart = selectionEnd = 0;
                } else {
                  selectionStart = 0;
                  selectionEnd = 1;
                }
              }
            }
            var newValue = line + "\n\n";
            if (newValue != lastValue) {
              text.value = lastValue = newValue;
              lastSelectionStart = lastSelectionEnd = newValue.length;
            }
          }
          if (afterContextMenu) {
            lastSelectionStart = text.selectionStart;
            lastSelectionEnd = text.selectionEnd;
          }
          if (
            lastSelectionEnd != selectionEnd ||
            lastSelectionStart != selectionStart ||
            text.selectionEnd != lastSelectionEnd // on ie edge selectionEnd changes silently after the initialization
          ) {
            try {
              text.setSelectionRange(selectionStart, selectionEnd);
              lastSelectionStart = selectionStart;
              lastSelectionEnd = selectionEnd;
            } catch (e) {}
          }
          inComposition = false;
        };
    this.resetSelection = resetSelection;
    if (isFocused) host.onFocus();
    var isAllSelected = function (text) {
      return (
        text.selectionStart === 0 &&
        text.selectionEnd >= lastValue.length &&
        text.value === lastValue &&
        lastValue &&
        text.selectionEnd !== lastSelectionEnd
      );
    };
    var onSelect = function (e) {
      if (inComposition) return;
      if (copied) {
        copied = false;
      } else if (isAllSelected(text)) {
        host.selectAll();
        resetSelection();
      } else if (isMobile && text.selectionStart != lastSelectionStart) {
        resetSelection();
      }
    };
    var inputHandler = null;
    this.setInputHandler = function (cb) {
      inputHandler = cb;
    };
    this.getInputHandler = function () {
      return inputHandler;
    };
    var afterContextMenu = false;
    var sendText = function (value, fromInput) {
      if (afterContextMenu) afterContextMenu = false;
      if (pasted) {
        resetSelection();
        if (value) host.onPaste(value);
        pasted = false;
        return "";
      } else {
        var selectionStart = text.selectionStart;
        var selectionEnd = text.selectionEnd;
        var extendLeft = lastSelectionStart;
        var extendRight = lastValue.length - lastSelectionEnd;
        var inserted = value;
        var restoreStart = value.length - selectionStart;
        var restoreEnd = value.length - selectionEnd;
        var i = 0;
        while (extendLeft > 0 && lastValue[i] == value[i]) {
          i++;
          extendLeft--;
        }
        inserted = inserted.slice(i);
        i = 1;
        while (
          extendRight > 0 &&
          lastValue.length - i > lastSelectionStart - 1 &&
          lastValue[lastValue.length - i] == value[value.length - i]
        ) {
          i++;
          extendRight--;
        }
        restoreStart -= i - 1;
        restoreEnd -= i - 1;
        var endIndex = inserted.length - i + 1;
        if (endIndex < 0) {
          extendLeft = -endIndex;
          endIndex = 0;
        }
        inserted = inserted.slice(0, endIndex);
        if (
          !fromInput &&
          !inserted &&
          !restoreStart &&
          !extendLeft &&
          !extendRight &&
          !restoreEnd
        )
          return "";
        sendingText = true;
        var shouldReset = false;
        if (useragent.isAndroid && inserted == ". ") {
          inserted = "  ";
          shouldReset = true;
        }
        if (
          (inserted &&
            !extendLeft &&
            !extendRight &&
            !restoreStart &&
            !restoreEnd) ||
          commandMode
        ) {
          host.onTextInput(inserted);
        } else {
          host.onTextInput(inserted, {
            extendLeft: extendLeft,
            extendRight: extendRight,
            restoreStart: restoreStart,
            restoreEnd: restoreEnd,
          });
        }
        sendingText = false;
        lastValue = value;
        lastSelectionStart = selectionStart;
        lastSelectionEnd = selectionEnd;
        lastRestoreEnd = restoreEnd;
        return shouldReset ? "\n" : inserted;
      }
    };
    var onInput = function (e) {
      if (inComposition) return onCompositionUpdate();
      if (e && e.inputType) {
        if (e.inputType == "historyUndo") return host.execCommand("undo");
        if (e.inputType == "historyRedo") return host.execCommand("redo");
      }
      var data = text.value;
      var inserted = sendText(data, true);
      if (
        data.length > MAX_LINE_LENGTH + 100 ||
        valueResetRegex.test(inserted) ||
        (isMobile &&
          lastSelectionStart < 1 &&
          lastSelectionStart == lastSelectionEnd)
      ) {
        resetSelection();
      }
    };
    var handleClipboardData = function (e, data, forceIEMime) {
      var clipboardData = e.clipboardData || window["clipboardData"];
      if (!clipboardData || BROKEN_SETDATA) return;
      var mime = USE_IE_MIME_TYPE || forceIEMime ? "Text" : "text/plain";
      try {
        if (data) {
          return clipboardData.setData(mime, data) !== false;
        } else {
          return clipboardData.getData(mime);
        }
      } catch (e) {
        if (!forceIEMime) return handleClipboardData(e, data, true);
      }
    };
    var doCopy = function (e, isCut) {
      var data = host.getCopyText();
      if (!data) return event.preventDefault(e);
      if (handleClipboardData(e, data)) {
        if (isIOS) {
          resetSelection(data);
          copied = data;
          setTimeout(function () {
            copied = false;
          }, 10);
        }
        isCut ? host.onCut() : host.onCopy();
        event.preventDefault(e);
      } else {
        copied = true;
        text.value = data;
        text.select();
        setTimeout(function () {
          copied = false;
          resetSelection();
          isCut ? host.onCut() : host.onCopy();
        });
      }
    };
    var onCut = function (e) {
      doCopy(e, true);
    };
    var onCopy = function (e) {
      doCopy(e, false);
    };
    var onPaste = function (e) {
      var data = handleClipboardData(e);
      if (clipboard.pasteCancelled()) return;
      if (typeof data == "string") {
        if (data) host.onPaste(data, e);
        if (useragent.isIE) setTimeout(resetSelection);
        event.preventDefault(e);
      } else {
        text.value = "";
        pasted = true;
      }
    };
    event.addCommandKeyListener(text, host.onCommandKey.bind(host), host);
    event.addListener(text, "select", onSelect, host);
    event.addListener(text, "input", onInput, host);
    event.addListener(text, "cut", onCut, host);
    event.addListener(text, "copy", onCopy, host);
    event.addListener(text, "paste", onPaste, host);
    if (!("oncut" in text) || !("oncopy" in text) || !("onpaste" in text)) {
      event.addListener(
        parentNode,
        "keydown",
        function (e) {
          if ((useragent.isMac && !e.metaKey) || !e.ctrlKey) return;
          switch (e.keyCode) {
            case 67:
              onCopy(e);
              break;
            case 86:
              onPaste(e);
              break;
            case 88:
              onCut(e);
              break;
          }
        },
        host,
      );
    }
    var onCompositionStart = function (e) {
      if (inComposition || !host.onCompositionStart || host.$readOnly) return;
      inComposition = {};
      if (commandMode) return;
      if (e.data) inComposition.useTextareaForIME = false;
      setTimeout(onCompositionUpdate, 0);
      host._signal("compositionStart");
      host.on("mousedown", cancelComposition);
      var range = host.getSelectionRange();
      range.end.row = range.start.row;
      range.end.column = range.start.column;
      inComposition.markerRange = range;
      inComposition.selectionStart = lastSelectionStart;
      host.onCompositionStart(inComposition);
      if (inComposition.useTextareaForIME) {
        lastValue = text.value = "";
        lastSelectionStart = 0;
        lastSelectionEnd = 0;
      } else {
        if (text.msGetInputContext)
          inComposition.context = text.msGetInputContext();
        if (text.getInputContext)
          inComposition.context = text.getInputContext();
      }
    };
    var onCompositionUpdate = function () {
      if (!inComposition || !host.onCompositionUpdate || host.$readOnly) return;
      if (commandMode) return cancelComposition();
      if (inComposition.useTextareaForIME) {
        host.onCompositionUpdate(text.value);
      } else {
        var data = text.value;
        sendText(data);
        if (inComposition.markerRange) {
          if (inComposition.context) {
            inComposition.markerRange.start.column =
              inComposition.selectionStart =
                inComposition.context.compositionStartOffset;
          }
          inComposition.markerRange.end.column =
            inComposition.markerRange.start.column +
            lastSelectionEnd -
            inComposition.selectionStart +
            lastRestoreEnd;
        }
      }
    };
    var onCompositionEnd = function (e) {
      if (!host.onCompositionEnd || host.$readOnly) return;
      inComposition = false;
      host.onCompositionEnd();
      host.off("mousedown", cancelComposition);
      if (e) onInput();
    };
    function cancelComposition() {
      ignoreFocusEvents = true;
      text.blur();
      text.focus();
      ignoreFocusEvents = false;
    }
    var syncComposition = lang
      .delayedCall(onCompositionUpdate, 50)
      .schedule.bind(null, null);
    function onKeyup(e) {
      if (e.keyCode == 27 && text.value.length < text.selectionStart) {
        if (!inComposition) lastValue = text.value;
        lastSelectionStart = lastSelectionEnd = -1;
        resetSelection();
      }
      syncComposition();
    }
    event.addListener(text, "compositionstart", onCompositionStart, host);
    event.addListener(text, "compositionupdate", onCompositionUpdate, host);
    event.addListener(text, "keyup", onKeyup, host);
    event.addListener(text, "keydown", syncComposition, host);
    event.addListener(text, "compositionend", onCompositionEnd, host);
    this.getElement = function () {
      return text;
    };
    this.setCommandMode = function (value) {
      commandMode = value;
      text.readOnly = false;
    };
    this.setReadOnly = function (readOnly) {
      if (!commandMode) text.readOnly = readOnly;
    };
    this.setCopyWithEmptySelection = function (value) {};
    this.onContextMenu = function (e) {
      afterContextMenu = true;
      resetSelection();
      host._emit("nativecontextmenu", { target: host, domEvent: e });
      this.moveToMouse(e, true);
    };
    this.moveToMouse = function (e, bringToFront) {
      if (!tempStyle) tempStyle = text.style.cssText;
      text.style.cssText =
        (bringToFront ? "z-index:100000;" : "") +
        (useragent.isIE ? "opacity:0.1;" : "") +
        "text-indent: -" +
        (lastSelectionStart + lastSelectionEnd) *
          host.renderer.characterWidth *
          0.5 +
        "px;";
      var rect = host.container.getBoundingClientRect();
      var style = dom.computedStyle(host.container);
      var top = rect.top + (parseInt(style.borderTopWidth) || 0);
      var left = rect.left + (parseInt(rect.borderLeftWidth) || 0);
      var maxTop = rect.bottom - top - text.clientHeight - 2;
      var move = function (e) {
        dom.translate(
          text,
          e.clientX - left - 2,
          Math.min(e.clientY - top - 2, maxTop),
        );
      };
      move(e);
      if (e.type != "mousedown") return;
      host.renderer.$isMousePressed = true;
      clearTimeout(closeTimeout);
      if (useragent.isWin)
        event.capture(host.container, move, onContextMenuClose);
    };
    this.onContextMenuClose = onContextMenuClose;
    var closeTimeout;
    function onContextMenuClose() {
      clearTimeout(closeTimeout);
      closeTimeout = setTimeout(function () {
        if (tempStyle) {
          text.style.cssText = tempStyle;
          tempStyle = "";
        }
        host.renderer.$isMousePressed = false;
        if (host.renderer.$keepTextAreaAtCursor)
          host.renderer.$moveTextAreaToCursor();
      }, 0);
    }
    var onContextMenu = function (e) {
      host.textInput.onContextMenu(e);
      onContextMenuClose();
    };
    event.addListener(text, "mouseup", onContextMenu, host);
    event.addListener(
      text,
      "mousedown",
      function (e) {
        e.preventDefault();
        onContextMenuClose();
      },
      host,
    );
    event.addListener(
      host.renderer.scroller,
      "contextmenu",
      onContextMenu,
      host,
    );
    event.addListener(text, "contextmenu", onContextMenu, host);
    if (isIOS) addIosSelectionHandler(parentNode, host, text);
    function addIosSelectionHandler(parentNode, host, text) {
      var typingResetTimeout = null;
      var typing = false;
      text.addEventListener(
        "keydown",
        function (e) {
          if (typingResetTimeout) clearTimeout(typingResetTimeout);
          typing = true;
        },
        true,
      );
      text.addEventListener(
        "keyup",
        function (e) {
          typingResetTimeout = setTimeout(function () {
            typing = false;
          }, 100);
        },
        true,
      );
      var detectArrowKeys = function (e) {
        if (document.activeElement !== text) return;
        if (typing || inComposition || host.$mouseHandler.isMousePressed)
          return;
        if (copied) {
          return;
        }
        var selectionStart = text.selectionStart;
        var selectionEnd = text.selectionEnd;
        var key = null;
        var modifier = 0;
        if (selectionStart == 0) {
          key = KEYS.up;
        } else if (selectionStart == 1) {
          key = KEYS.home;
        } else if (
          selectionEnd > lastSelectionEnd &&
          lastValue[selectionEnd] == "\n"
        ) {
          key = KEYS.end;
        } else if (
          selectionStart < lastSelectionStart &&
          lastValue[selectionStart - 1] == " "
        ) {
          key = KEYS.left;
          modifier = MODS.option;
        } else if (
          selectionStart < lastSelectionStart ||
          (selectionStart == lastSelectionStart &&
            lastSelectionEnd != lastSelectionStart &&
            selectionStart == selectionEnd)
        ) {
          key = KEYS.left;
        } else if (
          selectionEnd > lastSelectionEnd &&
          lastValue.slice(0, selectionEnd).split("\n").length > 2
        ) {
          key = KEYS.down;
        } else if (
          selectionEnd > lastSelectionEnd &&
          lastValue[selectionEnd - 1] == " "
        ) {
          key = KEYS.right;
          modifier = MODS.option;
        } else if (
          selectionEnd > lastSelectionEnd ||
          (selectionEnd == lastSelectionEnd &&
            lastSelectionEnd != lastSelectionStart &&
            selectionStart == selectionEnd)
        ) {
          key = KEYS.right;
        }
        if (selectionStart !== selectionEnd) modifier |= MODS.shift;
        if (key) {
          var result = host.onCommandKey({}, modifier, key);
          if (!result && host.commands) {
            key = KEYS.keyCodeToString(key);
            var command = host.commands.findKeyCommand(modifier, key);
            if (command) host.execCommand(command);
          }
          lastSelectionStart = selectionStart;
          lastSelectionEnd = selectionEnd;
          resetSelection("");
        }
      };
      document.addEventListener("selectionchange", detectArrowKeys);
      host.on("destroy", function () {
        document.removeEventListener("selectionchange", detectArrowKeys);
      });
    }
    this.destroy = function () {
      if (text.parentElement) text.parentElement.removeChild(text);
    };
  };
  exports.TextInput = TextInput;
  exports.$setUserAgentForTests = function (_isMobile, _isIOS) {
    isMobile = _isMobile;
    isIOS = _isIOS;
  };
});

define("ace/mouse/default_handlers", [
  "require",
  "exports",
  "module",
  "ace/lib/useragent",
], function (require, exports, module) {
  "use strict";
  var useragent = require("../lib/useragent");
  var DRAG_OFFSET = 0; // pixels
  var SCROLL_COOLDOWN_T = 550; // milliseconds
  var DefaultHandlers = /** @class */ (function () {
    function DefaultHandlers(mouseHandler) {
      mouseHandler.$clickSelection = null;
      var editor = mouseHandler.editor;
      editor.setDefaultHandler(
        "mousedown",
        this.onMouseDown.bind(mouseHandler),
      );
      editor.setDefaultHandler(
        "dblclick",
        this.onDoubleClick.bind(mouseHandler),
      );
      editor.setDefaultHandler(
        "tripleclick",
        this.onTripleClick.bind(mouseHandler),
      );
      editor.setDefaultHandler(
        "quadclick",
        this.onQuadClick.bind(mouseHandler),
      );
      editor.setDefaultHandler(
        "mousewheel",
        this.onMouseWheel.bind(mouseHandler),
      );
      var exports = [
        "select",
        "startSelect",
        "selectEnd",
        "selectAllEnd",
        "selectByWordsEnd",
        "selectByLinesEnd",
        "dragWait",
        "dragWaitEnd",
        "focusWait",
      ];
      exports.forEach(function (x) {
        mouseHandler[x] = this[x];
      }, this);
      mouseHandler["selectByLines"] = this.extendSelectionBy.bind(
        mouseHandler,
        "getLineRange",
      );
      mouseHandler["selectByWords"] = this.extendSelectionBy.bind(
        mouseHandler,
        "getWordRange",
      );
    }
    DefaultHandlers.prototype.onMouseDown = function (ev) {
      var inSelection = ev.inSelection();
      var pos = ev.getDocumentPosition();
      this.mousedownEvent = ev;
      var editor = this.editor;
      var button = ev.getButton();
      if (button !== 0) {
        var selectionRange = editor.getSelectionRange();
        var selectionEmpty = selectionRange.isEmpty();
        if (selectionEmpty || button == 1) editor.selection.moveToPosition(pos);
        if (button == 2) {
          editor.textInput.onContextMenu(ev.domEvent);
          if (!useragent.isMozilla) ev.preventDefault();
        }
        return;
      }
      this.mousedownEvent.time = Date.now();
      if (inSelection && !editor.isFocused()) {
        editor.focus();
        if (
          this.$focusTimeout &&
          !this.$clickSelection &&
          !editor.inMultiSelectMode
        ) {
          this.setState("focusWait");
          this.captureMouse(ev);
          return;
        }
      }
      this.captureMouse(ev);
      this.startSelect(pos, ev.domEvent._clicks > 1);
      return ev.preventDefault();
    };
    DefaultHandlers.prototype.startSelect = function (
      pos,
      waitForClickSelection,
    ) {
      pos = pos || this.editor.renderer.screenToTextCoordinates(this.x, this.y);
      var editor = this.editor;
      if (!this.mousedownEvent) return;
      if (this.mousedownEvent.getShiftKey())
        editor.selection.selectToPosition(pos);
      else if (!waitForClickSelection) editor.selection.moveToPosition(pos);
      if (!waitForClickSelection) this.select();
      editor.setStyle("ace_selecting");
      this.setState("select");
    };
    DefaultHandlers.prototype.select = function () {
      var anchor,
        editor = this.editor;
      var cursor = editor.renderer.screenToTextCoordinates(this.x, this.y);
      if (this.$clickSelection) {
        var cmp = this.$clickSelection.comparePoint(cursor);
        if (cmp == -1) {
          anchor = this.$clickSelection.end;
        } else if (cmp == 1) {
          anchor = this.$clickSelection.start;
        } else {
          var orientedRange = calcRangeOrientation(
            this.$clickSelection,
            cursor,
          );
          cursor = orientedRange.cursor;
          anchor = orientedRange.anchor;
        }
        editor.selection.setSelectionAnchor(anchor.row, anchor.column);
      }
      editor.selection.selectToPosition(cursor);
      editor.renderer.scrollCursorIntoView();
    };
    DefaultHandlers.prototype.extendSelectionBy = function (unitName) {
      var anchor,
        editor = this.editor;
      var cursor = editor.renderer.screenToTextCoordinates(this.x, this.y);
      var range = editor.selection[unitName](cursor.row, cursor.column);
      if (this.$clickSelection) {
        var cmpStart = this.$clickSelection.comparePoint(range.start);
        var cmpEnd = this.$clickSelection.comparePoint(range.end);
        if (cmpStart == -1 && cmpEnd <= 0) {
          anchor = this.$clickSelection.end;
          if (range.end.row != cursor.row || range.end.column != cursor.column)
            cursor = range.start;
        } else if (cmpEnd == 1 && cmpStart >= 0) {
          anchor = this.$clickSelection.start;
          if (
            range.start.row != cursor.row ||
            range.start.column != cursor.column
          )
            cursor = range.end;
        } else if (cmpStart == -1 && cmpEnd == 1) {
          cursor = range.end;
          anchor = range.start;
        } else {
          var orientedRange = calcRangeOrientation(
            this.$clickSelection,
            cursor,
          );
          cursor = orientedRange.cursor;
          anchor = orientedRange.anchor;
        }
        editor.selection.setSelectionAnchor(anchor.row, anchor.column);
      }
      editor.selection.selectToPosition(cursor);
      editor.renderer.scrollCursorIntoView();
    };
    DefaultHandlers.prototype.selectByLinesEnd = function () {
      this.$clickSelection = null;
      this.editor.unsetStyle("ace_selecting");
    };
    DefaultHandlers.prototype.focusWait = function () {
      var distance = calcDistance(
        this.mousedownEvent.x,
        this.mousedownEvent.y,
        this.x,
        this.y,
      );
      var time = Date.now();
      if (
        distance > DRAG_OFFSET ||
        time - this.mousedownEvent.time > this.$focusTimeout
      )
        this.startSelect(this.mousedownEvent.getDocumentPosition());
    };
    DefaultHandlers.prototype.onDoubleClick = function (ev) {
      var pos = ev.getDocumentPosition();
      var editor = this.editor;
      var session = editor.session;
      var range = session.getBracketRange(pos);
      if (range) {
        if (range.isEmpty()) {
          range.start.column--;
          range.end.column++;
        }
        this.setState("select");
      } else {
        range = editor.selection.getWordRange(pos.row, pos.column);
        this.setState("selectByWords");
      }
      this.$clickSelection = range;
      this.select();
    };
    DefaultHandlers.prototype.onTripleClick = function (ev) {
      var pos = ev.getDocumentPosition();
      var editor = this.editor;
      this.setState("selectByLines");
      var range = editor.getSelectionRange();
      if (range.isMultiLine() && range.contains(pos.row, pos.column)) {
        this.$clickSelection = editor.selection.getLineRange(range.start.row);
        this.$clickSelection.end = editor.selection.getLineRange(
          range.end.row,
        ).end;
      } else {
        this.$clickSelection = editor.selection.getLineRange(pos.row);
      }
      this.select();
    };
    DefaultHandlers.prototype.onQuadClick = function (ev) {
      var editor = this.editor;
      editor.selectAll();
      this.$clickSelection = editor.getSelectionRange();
      this.setState("selectAll");
    };
    DefaultHandlers.prototype.onMouseWheel = function (ev) {
      if (ev.getAccelKey()) return;
      if (ev.getShiftKey() && ev.wheelY && !ev.wheelX) {
        ev.wheelX = ev.wheelY;
        ev.wheelY = 0;
      }
      var editor = this.editor;
      if (!this.$lastScroll)
        this.$lastScroll = { t: 0, vx: 0, vy: 0, allowed: 0 };
      var prevScroll = this.$lastScroll;
      var t = ev.domEvent.timeStamp;
      var dt = t - prevScroll.t;
      var vx = dt ? ev.wheelX / dt : prevScroll.vx;
      var vy = dt ? ev.wheelY / dt : prevScroll.vy;
      if (dt < SCROLL_COOLDOWN_T) {
        vx = (vx + prevScroll.vx) / 2;
        vy = (vy + prevScroll.vy) / 2;
      }
      var direction = Math.abs(vx / vy);
      var canScroll = false;
      if (
        direction >= 1 &&
        editor.renderer.isScrollableBy(ev.wheelX * ev.speed, 0)
      )
        canScroll = true;
      if (
        direction <= 1 &&
        editor.renderer.isScrollableBy(0, ev.wheelY * ev.speed)
      )
        canScroll = true;
      if (canScroll) {
        prevScroll.allowed = t;
      } else if (t - prevScroll.allowed < SCROLL_COOLDOWN_T) {
        var isSlower =
          Math.abs(vx) <= 1.5 * Math.abs(prevScroll.vx) &&
          Math.abs(vy) <= 1.5 * Math.abs(prevScroll.vy);
        if (isSlower) {
          canScroll = true;
          prevScroll.allowed = t;
        } else {
          prevScroll.allowed = 0;
        }
      }
      prevScroll.t = t;
      prevScroll.vx = vx;
      prevScroll.vy = vy;
      if (canScroll) {
        editor.renderer.scrollBy(ev.wheelX * ev.speed, ev.wheelY * ev.speed);
        return ev.stop();
      }
    };
    return DefaultHandlers;
  })();
  DefaultHandlers.prototype.selectEnd =
    DefaultHandlers.prototype.selectByLinesEnd;
  DefaultHandlers.prototype.selectAllEnd =
    DefaultHandlers.prototype.selectByLinesEnd;
  DefaultHandlers.prototype.selectByWordsEnd =
    DefaultHandlers.prototype.selectByLinesEnd;
  exports.DefaultHandlers = DefaultHandlers;
  function calcDistance(ax, ay, bx, by) {
    return Math.sqrt(Math.pow(bx - ax, 2) + Math.pow(by - ay, 2));
  }
  function calcRangeOrientation(range, cursor) {
    if (range.start.row == range.end.row)
      var cmp = 2 * cursor.column - range.start.column - range.end.column;
    else if (
      range.start.row == range.end.row - 1 &&
      !range.start.column &&
      !range.end.column
    )
      var cmp = cursor.column - 4;
    else var cmp = 2 * cursor.row - range.start.row - range.end.row;
    if (cmp < 0) return { cursor: range.start, anchor: range.end };
    else return { cursor: range.end, anchor: range.start };
  }
});

define("ace/lib/scroll", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  exports.preventParentScroll = function preventParentScroll(event) {
    event.stopPropagation();
    var target = event.currentTarget;
    var contentOverflows = target.scrollHeight > target.clientHeight;
    if (!contentOverflows) {
      event.preventDefault();
    }
  };
});

define("ace/tooltip", [
  "require",
  "exports",
  "module",
  "ace/lib/dom",
  "ace/lib/event",
  "ace/range",
  "ace/lib/scroll",
], function (require, exports, module) {
  "use strict";
  var __extends =
    (this && this.__extends) ||
    (function () {
      var extendStatics = function (d, b) {
        extendStatics =
          Object.setPrototypeOf ||
          ({ __proto__: [] } instanceof Array &&
            function (d, b) {
              d.__proto__ = b;
            }) ||
          function (d, b) {
            for (var p in b)
              if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p];
          };
        return extendStatics(d, b);
      };
      return function (d, b) {
        if (typeof b !== "function" && b !== null)
          throw new TypeError(
            "Class extends value " +
              String(b) +
              " is not a constructor or null",
          );
        extendStatics(d, b);
        function __() {
          this.constructor = d;
        }
        d.prototype =
          b === null
            ? Object.create(b)
            : ((__.prototype = b.prototype), new __());
      };
    })();
  var __values =
    (this && this.__values) ||
    function (o) {
      var s = typeof Symbol === "function" && Symbol.iterator,
        m = s && o[s],
        i = 0;
      if (m) return m.call(o);
      if (o && typeof o.length === "number")
        return {
          next: function () {
            if (o && i >= o.length) o = void 0;
            return { value: o && o[i++], done: !o };
          },
        };
      throw new TypeError(
        s ? "Object is not iterable." : "Symbol.iterator is not defined.",
      );
    };
  var dom = require("./lib/dom");
  var event = require("./lib/event");
  var Range = require("./range").Range;
  var preventParentScroll = require("./lib/scroll").preventParentScroll;
  var CLASSNAME = "ace_tooltip";
  var Tooltip = /** @class */ (function () {
    function Tooltip(parentNode) {
      this.isOpen = false;
      this.$element = null;
      this.$parentNode = parentNode;
    }
    Tooltip.prototype.$init = function () {
      this.$element = dom.createElement("div");
      this.$element.className = CLASSNAME;
      this.$element.style.display = "none";
      this.$parentNode.appendChild(this.$element);
      return this.$element;
    };
    Tooltip.prototype.getElement = function () {
      return this.$element || this.$init();
    };
    Tooltip.prototype.setText = function (text) {
      this.getElement().textContent = text;
    };
    Tooltip.prototype.setHtml = function (html) {
      this.getElement().innerHTML = html;
    };
    Tooltip.prototype.setPosition = function (x, y) {
      this.getElement().style.left = x + "px";
      this.getElement().style.top = y + "px";
    };
    Tooltip.prototype.setClassName = function (className) {
      dom.addCssClass(this.getElement(), className);
    };
    Tooltip.prototype.setTheme = function (theme) {
      this.$element.className =
        CLASSNAME +
        " " +
        (theme.isDark ? "ace_dark " : "") +
        (theme.cssClass || "");
    };
    Tooltip.prototype.show = function (text, x, y) {
      if (text != null) this.setText(text);
      if (x != null && y != null) this.setPosition(x, y);
      if (!this.isOpen) {
        this.getElement().style.display = "block";
        this.isOpen = true;
      }
    };
    Tooltip.prototype.hide = function (e) {
      if (this.isOpen) {
        this.getElement().style.display = "none";
        this.getElement().className = CLASSNAME;
        this.isOpen = false;
      }
    };
    Tooltip.prototype.getHeight = function () {
      return this.getElement().offsetHeight;
    };
    Tooltip.prototype.getWidth = function () {
      return this.getElement().offsetWidth;
    };
    Tooltip.prototype.destroy = function () {
      this.isOpen = false;
      if (this.$element && this.$element.parentNode) {
        this.$element.parentNode.removeChild(this.$element);
      }
    };
    return Tooltip;
  })();
  var PopupManager = /** @class */ (function () {
    function PopupManager() {
      this.popups = [];
    }
    PopupManager.prototype.addPopup = function (popup) {
      this.popups.push(popup);
      this.updatePopups();
    };
    PopupManager.prototype.removePopup = function (popup) {
      var index = this.popups.indexOf(popup);
      if (index !== -1) {
        this.popups.splice(index, 1);
        this.updatePopups();
      }
    };
    PopupManager.prototype.updatePopups = function () {
      var e_1, _a, e_2, _b;
      this.popups.sort(function (a, b) {
        return b.priority - a.priority;
      });
      var visiblepopups = [];
      try {
        for (
          var _c = __values(this.popups), _d = _c.next();
          !_d.done;
          _d = _c.next()
        ) {
          var popup = _d.value;
          var shouldDisplay = true;
          try {
            for (
              var visiblepopups_1 = ((e_2 = void 0), __values(visiblepopups)),
                visiblepopups_1_1 = visiblepopups_1.next();
              !visiblepopups_1_1.done;
              visiblepopups_1_1 = visiblepopups_1.next()
            ) {
              var visiblePopup = visiblepopups_1_1.value;
              if (this.doPopupsOverlap(visiblePopup, popup)) {
                shouldDisplay = false;
                break;
              }
            }
          } catch (e_2_1) {
            e_2 = { error: e_2_1 };
          } finally {
            try {
              if (
                visiblepopups_1_1 &&
                !visiblepopups_1_1.done &&
                (_b = visiblepopups_1.return)
              )
                _b.call(visiblepopups_1);
            } finally {
              if (e_2) throw e_2.error;
            }
          }
          if (shouldDisplay) {
            visiblepopups.push(popup);
          } else {
            popup.hide();
          }
        }
      } catch (e_1_1) {
        e_1 = { error: e_1_1 };
      } finally {
        try {
          if (_d && !_d.done && (_a = _c.return)) _a.call(_c);
        } finally {
          if (e_1) throw e_1.error;
        }
      }
    };
    PopupManager.prototype.doPopupsOverlap = function (popupA, popupB) {
      var rectA = popupA.getElement().getBoundingClientRect();
      var rectB = popupB.getElement().getBoundingClientRect();
      return (
        rectA.left < rectB.right &&
        rectA.right > rectB.left &&
        rectA.top < rectB.bottom &&
        rectA.bottom > rectB.top
      );
    };
    return PopupManager;
  })();
  var popupManager = new PopupManager();
  exports.popupManager = popupManager;
  exports.Tooltip = Tooltip;
  var HoverTooltip = /** @class */ (function (_super) {
    __extends(HoverTooltip, _super);
    function HoverTooltip(parentNode) {
      if (parentNode === void 0) {
        parentNode = document.body;
      }
      var _this = _super.call(this, parentNode) || this;
      _this.timeout = undefined;
      _this.lastT = 0;
      _this.idleTime = 350;
      _this.lastEvent = undefined;
      _this.onMouseOut = _this.onMouseOut.bind(_this);
      _this.onMouseMove = _this.onMouseMove.bind(_this);
      _this.waitForHover = _this.waitForHover.bind(_this);
      _this.hide = _this.hide.bind(_this);
      var el = _this.getElement();
      el.style.whiteSpace = "pre-wrap";
      el.style.pointerEvents = "auto";
      el.addEventListener("mouseout", _this.onMouseOut);
      el.tabIndex = -1;
      el.addEventListener(
        "blur",
        function () {
          if (!el.contains(document.activeElement)) this.hide();
        }.bind(_this),
      );
      el.addEventListener("wheel", preventParentScroll);
      return _this;
    }
    HoverTooltip.prototype.addToEditor = function (editor) {
      editor.on("mousemove", this.onMouseMove);
      editor.on("mousedown", this.hide);
      editor.renderer
        .getMouseEventTarget()
        .addEventListener("mouseout", this.onMouseOut, true);
    };
    HoverTooltip.prototype.removeFromEditor = function (editor) {
      editor.off("mousemove", this.onMouseMove);
      editor.off("mousedown", this.hide);
      editor.renderer
        .getMouseEventTarget()
        .removeEventListener("mouseout", this.onMouseOut, true);
      if (this.timeout) {
        clearTimeout(this.timeout);
        this.timeout = null;
      }
    };
    HoverTooltip.prototype.onMouseMove = function (e, editor) {
      this.lastEvent = e;
      this.lastT = Date.now();
      var isMousePressed = editor.$mouseHandler.isMousePressed;
      if (this.isOpen) {
        var pos = this.lastEvent && this.lastEvent.getDocumentPosition();
        if (
          !this.range ||
          !this.range.contains(pos.row, pos.column) ||
          isMousePressed ||
          this.isOutsideOfText(this.lastEvent)
        ) {
          this.hide();
        }
      }
      if (this.timeout || isMousePressed) return;
      this.lastEvent = e;
      this.timeout = setTimeout(this.waitForHover, this.idleTime);
    };
    HoverTooltip.prototype.waitForHover = function () {
      if (this.timeout) clearTimeout(this.timeout);
      var dt = Date.now() - this.lastT;
      if (this.idleTime - dt > 10) {
        this.timeout = setTimeout(this.waitForHover, this.idleTime - dt);
        return;
      }
      this.timeout = null;
      if (this.lastEvent && !this.isOutsideOfText(this.lastEvent)) {
        this.$gatherData(this.lastEvent, this.lastEvent.editor);
      }
    };
    HoverTooltip.prototype.isOutsideOfText = function (e) {
      var editor = e.editor;
      var docPos = e.getDocumentPosition();
      var line = editor.session.getLine(docPos.row);
      if (docPos.column == line.length) {
        var screenPos = editor.renderer.pixelToScreenCoordinates(
          e.clientX,
          e.clientY,
        );
        var clippedPos = editor.session.documentToScreenPosition(
          docPos.row,
          docPos.column,
        );
        if (
          clippedPos.column != screenPos.column ||
          clippedPos.row != screenPos.row
        ) {
          return true;
        }
      }
      return false;
    };
    HoverTooltip.prototype.setDataProvider = function (value) {
      this.$gatherData = value;
    };
    HoverTooltip.prototype.showForRange = function (
      editor,
      range,
      domNode,
      startingEvent,
    ) {
      var MARGIN = 10;
      if (startingEvent && startingEvent != this.lastEvent) return;
      if (this.isOpen && document.activeElement == this.getElement()) return;
      var renderer = editor.renderer;
      if (!this.isOpen) {
        popupManager.addPopup(this);
        this.$registerCloseEvents();
        this.setTheme(renderer.theme);
      }
      this.isOpen = true;
      this.addMarker(range, editor.session);
      this.range = Range.fromPoints(range.start, range.end);
      var position = renderer.textToScreenCoordinates(
        range.start.row,
        range.start.column,
      );
      var rect = renderer.scroller.getBoundingClientRect();
      if (position.pageX < rect.left) position.pageX = rect.left;
      var element = this.getElement();
      element.innerHTML = "";
      element.appendChild(domNode);
      element.style.maxHeight = "";
      element.style.display = "block";
      var labelHeight = element.clientHeight;
      var labelWidth = element.clientWidth;
      var spaceBelow =
        window.innerHeight - position.pageY - renderer.lineHeight;
      var isAbove = true;
      if (position.pageY - labelHeight < 0 && position.pageY < spaceBelow) {
        isAbove = false;
      }
      element.style.maxHeight =
        (isAbove ? position.pageY : spaceBelow) - MARGIN + "px";
      element.style.top = isAbove
        ? ""
        : position.pageY + renderer.lineHeight + "px";
      element.style.bottom = isAbove
        ? window.innerHeight - position.pageY + "px"
        : "";
      element.style.left =
        Math.min(position.pageX, window.innerWidth - labelWidth - MARGIN) +
        "px";
    };
    HoverTooltip.prototype.addMarker = function (range, session) {
      if (this.marker) {
        this.$markerSession.removeMarker(this.marker);
      }
      this.$markerSession = session;
      this.marker =
        session && session.addMarker(range, "ace_highlight-marker", "text");
    };
    HoverTooltip.prototype.hide = function (e) {
      if (!e && document.activeElement == this.getElement()) return;
      if (
        e &&
        e.target &&
        (e.type != "keydown" || e.ctrlKey || e.metaKey) &&
        this.$element.contains(e.target)
      )
        return;
      this.lastEvent = null;
      if (this.timeout) clearTimeout(this.timeout);
      this.timeout = null;
      this.addMarker(null);
      if (this.isOpen) {
        this.$removeCloseEvents();
        this.getElement().style.display = "none";
        this.isOpen = false;
        popupManager.removePopup(this);
      }
    };
    HoverTooltip.prototype.$registerCloseEvents = function () {
      window.addEventListener("keydown", this.hide, true);
      window.addEventListener("wheel", this.hide, true);
      window.addEventListener("mousedown", this.hide, true);
    };
    HoverTooltip.prototype.$removeCloseEvents = function () {
      window.removeEventListener("keydown", this.hide, true);
      window.removeEventListener("wheel", this.hide, true);
      window.removeEventListener("mousedown", this.hide, true);
    };
    HoverTooltip.prototype.onMouseOut = function (e) {
      if (this.timeout) {
        clearTimeout(this.timeout);
        this.timeout = null;
      }
      this.lastEvent = null;
      if (!this.isOpen) return;
      if (!e.relatedTarget || this.getElement().contains(e.relatedTarget))
        return;
      if (e && e.currentTarget.contains(e.relatedTarget)) return;
      if (!e.relatedTarget.classList.contains("ace_content")) this.hide();
    };
    return HoverTooltip;
  })(Tooltip);
  exports.HoverTooltip = HoverTooltip;
});

define("ace/mouse/default_gutter_handler", [
  "require",
  "exports",
  "module",
  "ace/lib/dom",
  "ace/lib/event",
  "ace/tooltip",
  "ace/config",
], function (require, exports, module) {
  "use strict";
  var __extends =
    (this && this.__extends) ||
    (function () {
      var extendStatics = function (d, b) {
        extendStatics =
          Object.setPrototypeOf ||
          ({ __proto__: [] } instanceof Array &&
            function (d, b) {
              d.__proto__ = b;
            }) ||
          function (d, b) {
            for (var p in b)
              if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p];
          };
        return extendStatics(d, b);
      };
      return function (d, b) {
        if (typeof b !== "function" && b !== null)
          throw new TypeError(
            "Class extends value " +
              String(b) +
              " is not a constructor or null",
          );
        extendStatics(d, b);
        function __() {
          this.constructor = d;
        }
        d.prototype =
          b === null
            ? Object.create(b)
            : ((__.prototype = b.prototype), new __());
      };
    })();
  var __values =
    (this && this.__values) ||
    function (o) {
      var s = typeof Symbol === "function" && Symbol.iterator,
        m = s && o[s],
        i = 0;
      if (m) return m.call(o);
      if (o && typeof o.length === "number")
        return {
          next: function () {
            if (o && i >= o.length) o = void 0;
            return { value: o && o[i++], done: !o };
          },
        };
      throw new TypeError(
        s ? "Object is not iterable." : "Symbol.iterator is not defined.",
      );
    };
  var dom = require("../lib/dom");
  var event = require("../lib/event");
  var Tooltip = require("../tooltip").Tooltip;
  var nls = require("../config").nls;
  function GutterHandler(mouseHandler) {
    var editor = mouseHandler.editor;
    var gutter = editor.renderer.$gutterLayer;
    var tooltip = new GutterTooltip(editor);
    mouseHandler.editor.setDefaultHandler("guttermousedown", function (e) {
      if (!editor.isFocused() || e.getButton() != 0) return;
      var gutterRegion = gutter.getRegion(e);
      if (gutterRegion == "foldWidgets") return;
      var row = e.getDocumentPosition().row;
      var selection = editor.session.selection;
      if (e.getShiftKey()) selection.selectTo(row, 0);
      else {
        if (e.domEvent.detail == 2) {
          editor.selectAll();
          return e.preventDefault();
        }
        mouseHandler.$clickSelection = editor.selection.getLineRange(row);
      }
      mouseHandler.setState("selectByLines");
      mouseHandler.captureMouse(e);
      return e.preventDefault();
    });
    var tooltipTimeout, mouseEvent;
    function showTooltip() {
      var row = mouseEvent.getDocumentPosition().row;
      var maxRow = editor.session.getLength();
      if (row == maxRow) {
        var screenRow = editor.renderer.pixelToScreenCoordinates(
          0,
          mouseEvent.y,
        ).row;
        var pos = mouseEvent.$pos;
        if (screenRow > editor.session.documentToScreenRow(pos.row, pos.column))
          return hideTooltip();
      }
      tooltip.showTooltip(row);
      if (!tooltip.isOpen) return;
      editor.on("mousewheel", hideTooltip);
      if (mouseHandler.$tooltipFollowsMouse) {
        moveTooltip(mouseEvent);
      } else {
        var gutterRow = mouseEvent.getGutterRow();
        var gutterCell = gutter.$lines.get(gutterRow);
        if (gutterCell) {
          var gutterElement = gutterCell.element.querySelector(
            ".ace_gutter_annotation",
          );
          var rect = gutterElement.getBoundingClientRect();
          var style = tooltip.getElement().style;
          style.left = rect.right + "px";
          style.top = rect.bottom + "px";
        } else {
          moveTooltip(mouseEvent);
        }
      }
    }
    function hideTooltip() {
      if (tooltipTimeout) tooltipTimeout = clearTimeout(tooltipTimeout);
      if (tooltip.isOpen) {
        tooltip.hideTooltip();
        editor.off("mousewheel", hideTooltip);
      }
    }
    function moveTooltip(e) {
      tooltip.setPosition(e.x, e.y);
    }
    mouseHandler.editor.setDefaultHandler("guttermousemove", function (e) {
      var target = e.domEvent.target || e.domEvent.srcElement;
      if (dom.hasCssClass(target, "ace_fold-widget")) return hideTooltip();
      if (tooltip.isOpen && mouseHandler.$tooltipFollowsMouse) moveTooltip(e);
      mouseEvent = e;
      if (tooltipTimeout) return;
      tooltipTimeout = setTimeout(function () {
        tooltipTimeout = null;
        if (mouseEvent && !mouseHandler.isMousePressed) showTooltip();
        else hideTooltip();
      }, 50);
    });
    event.addListener(
      editor.renderer.$gutter,
      "mouseout",
      function (e) {
        mouseEvent = null;
        if (!tooltip.isOpen || tooltipTimeout) return;
        tooltipTimeout = setTimeout(function () {
          tooltipTimeout = null;
          hideTooltip();
        }, 50);
      },
      editor,
    );
    editor.on("changeSession", hideTooltip);
    editor.on("input", hideTooltip);
  }
  exports.GutterHandler = GutterHandler;
  var GutterTooltip = /** @class */ (function (_super) {
    __extends(GutterTooltip, _super);
    function GutterTooltip(editor) {
      var _this = _super.call(this, editor.container) || this;
      _this.editor = editor;
      return _this;
    }
    GutterTooltip.prototype.setPosition = function (x, y) {
      var windowWidth =
        window.innerWidth || document.documentElement.clientWidth;
      var windowHeight =
        window.innerHeight || document.documentElement.clientHeight;
      var width = this.getWidth();
      var height = this.getHeight();
      x += 15;
      y += 15;
      if (x + width > windowWidth) {
        x -= x + width - windowWidth;
      }
      if (y + height > windowHeight) {
        y -= 20 + height;
      }
      Tooltip.prototype.setPosition.call(this, x, y);
    };
    Object.defineProperty(GutterTooltip, "annotationLabels", {
      get: function () {
        return {
          error: { singular: nls("error"), plural: nls("errors") },
          warning: { singular: nls("warning"), plural: nls("warnings") },
          info: {
            singular: nls("information message"),
            plural: nls("information messages"),
          },
        };
      },
      enumerable: false,
      configurable: true,
    });
    GutterTooltip.prototype.showTooltip = function (row) {
      var gutter = this.editor.renderer.$gutterLayer;
      var annotationsInRow = gutter.$annotations[row];
      var annotation;
      if (annotationsInRow)
        annotation = {
          text: Array.from(annotationsInRow.text),
          type: Array.from(annotationsInRow.type),
        };
      else annotation = { text: [], type: [] };
      var fold = gutter.session.getFoldLine(row);
      if (fold && gutter.$showFoldedAnnotations) {
        var annotationsInFold = { error: [], warning: [], info: [] };
        var mostSevereAnnotationInFoldType;
        for (var i = row + 1; i <= fold.end.row; i++) {
          if (!gutter.$annotations[i]) continue;
          for (var j = 0; j < gutter.$annotations[i].text.length; j++) {
            var annotationType = gutter.$annotations[i].type[j];
            annotationsInFold[annotationType].push(
              gutter.$annotations[i].text[j],
            );
            if (annotationType === "error") {
              mostSevereAnnotationInFoldType = "error_fold";
              continue;
            }
            if (annotationType === "warning") {
              mostSevereAnnotationInFoldType = "warning_fold";
              continue;
            }
          }
        }
        if (
          mostSevereAnnotationInFoldType === "error_fold" ||
          mostSevereAnnotationInFoldType === "warning_fold"
        ) {
          var summaryFoldedAnnotations = "".concat(
            GutterTooltip.annotationsToSummaryString(annotationsInFold),
            " in folded code.",
          );
          annotation.text.push(summaryFoldedAnnotations);
          annotation.type.push(mostSevereAnnotationInFoldType);
        }
      }
      if (annotation.text.length === 0) return this.hide();
      var annotationMessages = { error: [], warning: [], info: [] };
      var iconClassName = gutter.$useSvgGutterIcons
        ? "ace_icon_svg"
        : "ace_icon";
      for (var i = 0; i < annotation.text.length; i++) {
        var line = "<span class='ace_"
          .concat(annotation.type[i], " ")
          .concat(iconClassName, "' aria-label='")
          .concat(
            GutterTooltip.annotationLabels[
              annotation.type[i].replace("_fold", "")
            ].singular,
            "' role=img> </span> ",
          )
          .concat(annotation.text[i]);
        annotationMessages[annotation.type[i].replace("_fold", "")].push(line);
      }
      var tooltipContent = []
        .concat(
          annotationMessages.error,
          annotationMessages.warning,
          annotationMessages.info,
        )
        .join("<br>");
      this.setHtml(tooltipContent);
      this.$element.setAttribute("aria-live", "polite");
      if (!this.isOpen) {
        this.setTheme(this.editor.renderer.theme);
        this.setClassName("ace_gutter-tooltip");
      }
      this.show();
      this.editor._signal("showGutterTooltip", this);
    };
    GutterTooltip.prototype.hideTooltip = function () {
      this.$element.removeAttribute("aria-live");
      this.hide();
      this.editor._signal("hideGutterTooltip", this);
    };
    GutterTooltip.annotationsToSummaryString = function (annotations) {
      var e_1, _a;
      var summary = [];
      var annotationTypes = ["error", "warning", "info"];
      try {
        for (
          var annotationTypes_1 = __values(annotationTypes),
            annotationTypes_1_1 = annotationTypes_1.next();
          !annotationTypes_1_1.done;
          annotationTypes_1_1 = annotationTypes_1.next()
        ) {
          var annotationType = annotationTypes_1_1.value;
          if (!annotations[annotationType].length) continue;
          var label =
            annotations[annotationType].length === 1
              ? GutterTooltip.annotationLabels[annotationType].singular
              : GutterTooltip.annotationLabels[annotationType].plural;
          summary.push(
            "".concat(annotations[annotationType].length, " ").concat(label),
          );
        }
      } catch (e_1_1) {
        e_1 = { error: e_1_1 };
      } finally {
        try {
          if (
            annotationTypes_1_1 &&
            !annotationTypes_1_1.done &&
            (_a = annotationTypes_1.return)
          )
            _a.call(annotationTypes_1);
        } finally {
          if (e_1) throw e_1.error;
        }
      }
      return summary.join(", ");
    };
    return GutterTooltip;
  })(Tooltip);
  exports.GutterTooltip = GutterTooltip;
});

define("ace/mouse/mouse_event", [
  "require",
  "exports",
  "module",
  "ace/lib/event",
  "ace/lib/useragent",
], function (require, exports, module) {
  "use strict";
  var event = require("../lib/event");
  var useragent = require("../lib/useragent");
  var MouseEvent = /** @class */ (function () {
    function MouseEvent(domEvent, editor) {
      this.speed;
      this.wheelX;
      this.wheelY;
      this.domEvent = domEvent;
      this.editor = editor;
      this.x = this.clientX = domEvent.clientX;
      this.y = this.clientY = domEvent.clientY;
      this.$pos = null;
      this.$inSelection = null;
      this.propagationStopped = false;
      this.defaultPrevented = false;
    }
    MouseEvent.prototype.stopPropagation = function () {
      event.stopPropagation(this.domEvent);
      this.propagationStopped = true;
    };
    MouseEvent.prototype.preventDefault = function () {
      event.preventDefault(this.domEvent);
      this.defaultPrevented = true;
    };
    MouseEvent.prototype.stop = function () {
      this.stopPropagation();
      this.preventDefault();
    };
    MouseEvent.prototype.getDocumentPosition = function () {
      if (this.$pos) return this.$pos;
      this.$pos = this.editor.renderer.screenToTextCoordinates(
        this.clientX,
        this.clientY,
      );
      return this.$pos;
    };
    MouseEvent.prototype.getGutterRow = function () {
      var documentRow = this.getDocumentPosition().row;
      var screenRow = this.editor.session.documentToScreenRow(documentRow, 0);
      var screenTopRow = this.editor.session.documentToScreenRow(
        this.editor.renderer.$gutterLayer.$lines.get(0).row,
        0,
      );
      return screenRow - screenTopRow;
    };
    MouseEvent.prototype.inSelection = function () {
      if (this.$inSelection !== null) return this.$inSelection;
      var editor = this.editor;
      var selectionRange = editor.getSelectionRange();
      if (selectionRange.isEmpty()) this.$inSelection = false;
      else {
        var pos = this.getDocumentPosition();
        this.$inSelection = selectionRange.contains(pos.row, pos.column);
      }
      return this.$inSelection;
    };
    MouseEvent.prototype.getButton = function () {
      return event.getButton(this.domEvent);
    };
    MouseEvent.prototype.getShiftKey = function () {
      return this.domEvent.shiftKey;
    };
    MouseEvent.prototype.getAccelKey = function () {
      return useragent.isMac ? this.domEvent.metaKey : this.domEvent.ctrlKey;
    };
    return MouseEvent;
  })();
  exports.MouseEvent = MouseEvent;
});

define("ace/mouse/dragdrop_handler", [
  "require",
  "exports",
  "module",
  "ace/lib/dom",
  "ace/lib/event",
  "ace/lib/useragent",
], function (require, exports, module) {
  "use strict";
  var dom = require("../lib/dom");
  var event = require("../lib/event");
  var useragent = require("../lib/useragent");
  var AUTOSCROLL_DELAY = 200;
  var SCROLL_CURSOR_DELAY = 200;
  var SCROLL_CURSOR_HYSTERESIS = 5;
  function DragdropHandler(mouseHandler) {
    var editor = mouseHandler.editor;
    var dragImage = dom.createElement("div");
    dragImage.style.cssText =
      "top:-100px;position:absolute;z-index:2147483647;opacity:0.5";
    dragImage.textContent = "\xa0";
    var exports = [
      "dragWait",
      "dragWaitEnd",
      "startDrag",
      "dragReadyEnd",
      "onMouseDrag",
    ];
    exports.forEach(function (x) {
      mouseHandler[x] = this[x];
    }, this);
    editor.on("mousedown", this.onMouseDown.bind(mouseHandler));
    var mouseTarget = editor.container;
    var dragSelectionMarker, x, y;
    var timerId, range;
    var dragCursor,
      counter = 0;
    var dragOperation;
    var isInternal;
    var autoScrollStartTime;
    var cursorMovedTime;
    var cursorPointOnCaretMoved;
    this.onDragStart = function (e) {
      if (this.cancelDrag || !mouseTarget.draggable) {
        var self = this;
        setTimeout(function () {
          self.startSelect();
          self.captureMouse(e);
        }, 0);
        return e.preventDefault();
      }
      range = editor.getSelectionRange();
      var dataTransfer = e.dataTransfer;
      dataTransfer.effectAllowed = editor.getReadOnly() ? "copy" : "copyMove";
      editor.container.appendChild(dragImage);
      dataTransfer.setDragImage && dataTransfer.setDragImage(dragImage, 0, 0);
      setTimeout(function () {
        editor.container.removeChild(dragImage);
      });
      dataTransfer.clearData();
      dataTransfer.setData("Text", editor.session.getTextRange());
      isInternal = true;
      this.setState("drag");
    };
    this.onDragEnd = function (e) {
      mouseTarget.draggable = false;
      isInternal = false;
      this.setState(null);
      if (!editor.getReadOnly()) {
        var dropEffect = e.dataTransfer.dropEffect;
        if (!dragOperation && dropEffect == "move")
          editor.session.remove(editor.getSelectionRange());
        editor.$resetCursorStyle();
      }
      this.editor.unsetStyle("ace_dragging");
      this.editor.renderer.setCursorStyle("");
    };
    this.onDragEnter = function (e) {
      if (editor.getReadOnly() || !canAccept(e.dataTransfer)) return;
      x = e.clientX;
      y = e.clientY;
      if (!dragSelectionMarker) addDragMarker();
      counter++;
      e.dataTransfer.dropEffect = dragOperation = getDropEffect(e);
      return event.preventDefault(e);
    };
    this.onDragOver = function (e) {
      if (editor.getReadOnly() || !canAccept(e.dataTransfer)) return;
      x = e.clientX;
      y = e.clientY;
      if (!dragSelectionMarker) {
        addDragMarker();
        counter++;
      }
      if (onMouseMoveTimer !== null) onMouseMoveTimer = null;
      e.dataTransfer.dropEffect = dragOperation = getDropEffect(e);
      return event.preventDefault(e);
    };
    this.onDragLeave = function (e) {
      counter--;
      if (counter <= 0 && dragSelectionMarker) {
        clearDragMarker();
        dragOperation = null;
        return event.preventDefault(e);
      }
    };
    this.onDrop = function (e) {
      if (!dragCursor) return;
      var dataTransfer = e.dataTransfer;
      if (isInternal) {
        switch (dragOperation) {
          case "move":
            if (range.contains(dragCursor.row, dragCursor.column)) {
              range = {
                start: dragCursor,
                end: dragCursor,
              };
            } else {
              range = editor.moveText(range, dragCursor);
            }
            break;
          case "copy":
            range = editor.moveText(range, dragCursor, true);
            break;
        }
      } else {
        var dropData = dataTransfer.getData("Text");
        range = {
          start: dragCursor,
          end: editor.session.insert(dragCursor, dropData),
        };
        editor.focus();
        dragOperation = null;
      }
      clearDragMarker();
      return event.preventDefault(e);
    };
    event.addListener(
      mouseTarget,
      "dragstart",
      this.onDragStart.bind(mouseHandler),
      editor,
    );
    event.addListener(
      mouseTarget,
      "dragend",
      this.onDragEnd.bind(mouseHandler),
      editor,
    );
    event.addListener(
      mouseTarget,
      "dragenter",
      this.onDragEnter.bind(mouseHandler),
      editor,
    );
    event.addListener(
      mouseTarget,
      "dragover",
      this.onDragOver.bind(mouseHandler),
      editor,
    );
    event.addListener(
      mouseTarget,
      "dragleave",
      this.onDragLeave.bind(mouseHandler),
      editor,
    );
    event.addListener(
      mouseTarget,
      "drop",
      this.onDrop.bind(mouseHandler),
      editor,
    );
    function scrollCursorIntoView(cursor, prevCursor) {
      var now = Date.now();
      var vMovement = !prevCursor || cursor.row != prevCursor.row;
      var hMovement = !prevCursor || cursor.column != prevCursor.column;
      if (!cursorMovedTime || vMovement || hMovement) {
        editor.moveCursorToPosition(cursor);
        cursorMovedTime = now;
        cursorPointOnCaretMoved = { x: x, y: y };
      } else {
        var distance = calcDistance(
          cursorPointOnCaretMoved.x,
          cursorPointOnCaretMoved.y,
          x,
          y,
        );
        if (distance > SCROLL_CURSOR_HYSTERESIS) {
          cursorMovedTime = null;
        } else if (now - cursorMovedTime >= SCROLL_CURSOR_DELAY) {
          editor.renderer.scrollCursorIntoView();
          cursorMovedTime = null;
        }
      }
    }
    function autoScroll(cursor, prevCursor) {
      var now = Date.now();
      var lineHeight = editor.renderer.layerConfig.lineHeight;
      var characterWidth = editor.renderer.layerConfig.characterWidth;
      var editorRect = editor.renderer.scroller.getBoundingClientRect();
      var offsets = {
        x: {
          left: x - editorRect.left,
          right: editorRect.right - x,
        },
        y: {
          top: y - editorRect.top,
          bottom: editorRect.bottom - y,
        },
      };
      var nearestXOffset = Math.min(offsets.x.left, offsets.x.right);
      var nearestYOffset = Math.min(offsets.y.top, offsets.y.bottom);
      var scrollCursor = { row: cursor.row, column: cursor.column };
      if (nearestXOffset / characterWidth <= 2) {
        scrollCursor.column += offsets.x.left < offsets.x.right ? -3 : +2;
      }
      if (nearestYOffset / lineHeight <= 1) {
        scrollCursor.row += offsets.y.top < offsets.y.bottom ? -1 : +1;
      }
      var vScroll = cursor.row != scrollCursor.row;
      var hScroll = cursor.column != scrollCursor.column;
      var vMovement = !prevCursor || cursor.row != prevCursor.row;
      if (vScroll || (hScroll && !vMovement)) {
        if (!autoScrollStartTime) autoScrollStartTime = now;
        else if (now - autoScrollStartTime >= AUTOSCROLL_DELAY)
          editor.renderer.scrollCursorIntoView(scrollCursor);
      } else {
        autoScrollStartTime = null;
      }
    }
    function onDragInterval() {
      var prevCursor = dragCursor;
      dragCursor = editor.renderer.screenToTextCoordinates(x, y);
      scrollCursorIntoView(dragCursor, prevCursor);
      autoScroll(dragCursor, prevCursor);
    }
    function addDragMarker() {
      range = editor.selection.toOrientedRange();
      dragSelectionMarker = editor.session.addMarker(
        range,
        "ace_selection",
        editor.getSelectionStyle(),
      );
      editor.clearSelection();
      if (editor.isFocused()) editor.renderer.$cursorLayer.setBlinking(false);
      clearInterval(timerId);
      onDragInterval();
      timerId = setInterval(onDragInterval, 20);
      counter = 0;
      event.addListener(document, "mousemove", onMouseMove);
    }
    function clearDragMarker() {
      clearInterval(timerId);
      editor.session.removeMarker(dragSelectionMarker);
      dragSelectionMarker = null;
      editor.selection.fromOrientedRange(range);
      if (editor.isFocused() && !isInternal) editor.$resetCursorStyle();
      range = null;
      dragCursor = null;
      counter = 0;
      autoScrollStartTime = null;
      cursorMovedTime = null;
      event.removeListener(document, "mousemove", onMouseMove);
    }
    var onMouseMoveTimer = null;
    function onMouseMove() {
      if (onMouseMoveTimer == null) {
        onMouseMoveTimer = setTimeout(function () {
          if (onMouseMoveTimer != null && dragSelectionMarker)
            clearDragMarker();
        }, 20);
      }
    }
    function canAccept(dataTransfer) {
      var types = dataTransfer.types;
      return (
        !types ||
        Array.prototype.some.call(types, function (type) {
          return type == "text/plain" || type == "Text";
        })
      );
    }
    function getDropEffect(e) {
      var copyAllowed = ["copy", "copymove", "all", "uninitialized"];
      var moveAllowed = [
        "move",
        "copymove",
        "linkmove",
        "all",
        "uninitialized",
      ];
      var copyModifierState = useragent.isMac ? e.altKey : e.ctrlKey;
      var effectAllowed = "uninitialized";
      try {
        effectAllowed = e.dataTransfer.effectAllowed.toLowerCase();
      } catch (e) {}
      var dropEffect = "none";
      if (copyModifierState && copyAllowed.indexOf(effectAllowed) >= 0)
        dropEffect = "copy";
      else if (moveAllowed.indexOf(effectAllowed) >= 0) dropEffect = "move";
      else if (copyAllowed.indexOf(effectAllowed) >= 0) dropEffect = "copy";
      return dropEffect;
    }
  }
  (function () {
    this.dragWait = function () {
      var interval = Date.now() - this.mousedownEvent.time;
      if (interval > this.editor.getDragDelay()) this.startDrag();
    };
    this.dragWaitEnd = function () {
      var target = this.editor.container;
      target.draggable = false;
      this.startSelect(this.mousedownEvent.getDocumentPosition());
      this.selectEnd();
    };
    this.dragReadyEnd = function (e) {
      this.editor.$resetCursorStyle();
      this.editor.unsetStyle("ace_dragging");
      this.editor.renderer.setCursorStyle("");
      this.dragWaitEnd();
    };
    this.startDrag = function () {
      this.cancelDrag = false;
      var editor = this.editor;
      var target = editor.container;
      target.draggable = true;
      editor.renderer.$cursorLayer.setBlinking(false);
      editor.setStyle("ace_dragging");
      var cursorStyle = useragent.isWin ? "default" : "move";
      editor.renderer.setCursorStyle(cursorStyle);
      this.setState("dragReady");
    };
    this.onMouseDrag = function (e) {
      var target = this.editor.container;
      if (useragent.isIE && this.state == "dragReady") {
        var distance = calcDistance(
          this.mousedownEvent.x,
          this.mousedownEvent.y,
          this.x,
          this.y,
        );
        if (distance > 3) target.dragDrop();
      }
      if (this.state === "dragWait") {
        var distance = calcDistance(
          this.mousedownEvent.x,
          this.mousedownEvent.y,
          this.x,
          this.y,
        );
        if (distance > 0) {
          target.draggable = false;
          this.startSelect(this.mousedownEvent.getDocumentPosition());
        }
      }
    };
    this.onMouseDown = function (e) {
      if (!this.$dragEnabled) return;
      this.mousedownEvent = e;
      var editor = this.editor;
      var inSelection = e.inSelection();
      var button = e.getButton();
      var clickCount = e.domEvent.detail || 1;
      if (clickCount === 1 && button === 0 && inSelection) {
        if (e.editor.inMultiSelectMode && (e.getAccelKey() || e.getShiftKey()))
          return;
        this.mousedownEvent.time = Date.now();
        var eventTarget = e.domEvent.target || e.domEvent.srcElement;
        if ("unselectable" in eventTarget) eventTarget.unselectable = "on";
        if (editor.getDragDelay()) {
          if (useragent.isWebKit) {
            this.cancelDrag = true;
            var mouseTarget = editor.container;
            mouseTarget.draggable = true;
          }
          this.setState("dragWait");
        } else {
          this.startDrag();
        }
        this.captureMouse(e, this.onMouseDrag.bind(this));
        e.defaultPrevented = true;
      }
    };
  }).call(DragdropHandler.prototype);
  function calcDistance(ax, ay, bx, by) {
    return Math.sqrt(Math.pow(bx - ax, 2) + Math.pow(by - ay, 2));
  }
  exports.DragdropHandler = DragdropHandler;
});

define("ace/mouse/touch_handler", [
  "require",
  "exports",
  "module",
  "ace/mouse/mouse_event",
  "ace/lib/event",
  "ace/lib/dom",
], function (require, exports, module) {
  "use strict";
  var MouseEvent = require("./mouse_event").MouseEvent;
  var event = require("../lib/event");
  var dom = require("../lib/dom");
  exports.addTouchListeners = function (el, editor) {
    var mode = "scroll";
    var startX;
    var startY;
    var touchStartT;
    var lastT;
    var longTouchTimer;
    var animationTimer;
    var animationSteps = 0;
    var pos;
    var clickCount = 0;
    var vX = 0;
    var vY = 0;
    var pressed;
    var contextMenu;
    function createContextMenu() {
      var clipboard = window.navigator && window.navigator.clipboard;
      var isOpen = false;
      var updateMenu = function () {
        var selected = editor.getCopyText();
        var hasUndo = editor.session.getUndoManager().hasUndo();
        contextMenu.replaceChild(
          dom.buildDom(
            isOpen
              ? [
                  "span",
                  !selected && [
                    "span",
                    { class: "ace_mobile-button", action: "selectall" },
                    "Select All",
                  ],
                  selected && [
                    "span",
                    { class: "ace_mobile-button", action: "copy" },
                    "Copy",
                  ],
                  selected && [
                    "span",
                    { class: "ace_mobile-button", action: "cut" },
                    "Cut",
                  ],
                  clipboard && [
                    "span",
                    { class: "ace_mobile-button", action: "paste" },
                    "Paste",
                  ],
                  hasUndo && [
                    "span",
                    { class: "ace_mobile-button", action: "undo" },
                    "Undo",
                  ],
                  [
                    "span",
                    { class: "ace_mobile-button", action: "find" },
                    "Find",
                  ],
                  [
                    "span",
                    {
                      class: "ace_mobile-button",
                      action: "openCommandPalette",
                    },
                    "Palette",
                  ],
                ]
              : ["span"],
          ),
          contextMenu.firstChild,
        );
      };
      var handleClick = function (e) {
        var action = e.target.getAttribute("action");
        if (action == "more" || !isOpen) {
          isOpen = !isOpen;
          return updateMenu();
        }
        if (action == "paste") {
          clipboard.readText().then(function (text) {
            editor.execCommand(action, text);
          });
        } else if (action) {
          if (action == "cut" || action == "copy") {
            if (clipboard) clipboard.writeText(editor.getCopyText());
            else document.execCommand("copy");
          }
          editor.execCommand(action);
        }
        contextMenu.firstChild.style.display = "none";
        isOpen = false;
        if (action != "openCommandPalette") editor.focus();
      };
      contextMenu = dom.buildDom(
        [
          "div",
          {
            class: "ace_mobile-menu",
            ontouchstart: function (e) {
              mode = "menu";
              e.stopPropagation();
              e.preventDefault();
              editor.textInput.focus();
            },
            ontouchend: function (e) {
              e.stopPropagation();
              e.preventDefault();
              handleClick(e);
            },
            onclick: handleClick,
          },
          ["span"],
          ["span", { class: "ace_mobile-button", action: "more" }, "..."],
        ],
        editor.container,
      );
    }
    function showContextMenu() {
      if (!contextMenu) createContextMenu();
      var cursor = editor.selection.cursor;
      var pagePos = editor.renderer.textToScreenCoordinates(
        cursor.row,
        cursor.column,
      );
      var leftOffset = editor.renderer.textToScreenCoordinates(0, 0).pageX;
      var scrollLeft = editor.renderer.scrollLeft;
      var rect = editor.container.getBoundingClientRect();
      contextMenu.style.top = pagePos.pageY - rect.top - 3 + "px";
      if (pagePos.pageX - rect.left < rect.width - 70) {
        contextMenu.style.left = "";
        contextMenu.style.right = "10px";
      } else {
        contextMenu.style.right = "";
        contextMenu.style.left = leftOffset + scrollLeft - rect.left + "px";
      }
      contextMenu.style.display = "";
      contextMenu.firstChild.style.display = "none";
      editor.on("input", hideContextMenu);
    }
    function hideContextMenu(e) {
      if (contextMenu) contextMenu.style.display = "none";
      editor.off("input", hideContextMenu);
    }
    function handleLongTap() {
      longTouchTimer = null;
      clearTimeout(longTouchTimer);
      var range = editor.selection.getRange();
      var inSelection = range.contains(pos.row, pos.column);
      if (range.isEmpty() || !inSelection) {
        editor.selection.moveToPosition(pos);
        editor.selection.selectWord();
      }
      mode = "wait";
      showContextMenu();
    }
    function switchToSelectionMode() {
      longTouchTimer = null;
      clearTimeout(longTouchTimer);
      editor.selection.moveToPosition(pos);
      var range =
        clickCount >= 2
          ? editor.selection.getLineRange(pos.row)
          : editor.session.getBracketRange(pos);
      if (range && !range.isEmpty()) {
        editor.selection.setRange(range);
      } else {
        editor.selection.selectWord();
      }
      mode = "wait";
    }
    event.addListener(
      el,
      "contextmenu",
      function (e) {
        if (!pressed) return;
        var textarea = editor.textInput.getElement();
        textarea.focus();
      },
      editor,
    );
    event.addListener(
      el,
      "touchstart",
      function (e) {
        var touches = e.touches;
        if (longTouchTimer || touches.length > 1) {
          clearTimeout(longTouchTimer);
          longTouchTimer = null;
          touchStartT = -1;
          mode = "zoom";
          return;
        }
        pressed = editor.$mouseHandler.isMousePressed = true;
        var h = editor.renderer.layerConfig.lineHeight;
        var w = editor.renderer.layerConfig.lineHeight;
        var t = e.timeStamp;
        lastT = t;
        var touchObj = touches[0];
        var x = touchObj.clientX;
        var y = touchObj.clientY;
        if (Math.abs(startX - x) + Math.abs(startY - y) > h) touchStartT = -1;
        startX = e.clientX = x;
        startY = e.clientY = y;
        vX = vY = 0;
        var ev = new MouseEvent(e, editor);
        pos = ev.getDocumentPosition();
        if (t - touchStartT < 500 && touches.length == 1 && !animationSteps) {
          clickCount++;
          e.preventDefault();
          e.button = 0;
          switchToSelectionMode();
        } else {
          clickCount = 0;
          var cursor = editor.selection.cursor;
          var anchor = editor.selection.isEmpty()
            ? cursor
            : editor.selection.anchor;
          var cursorPos = editor.renderer.$cursorLayer.getPixelPosition(
            cursor,
            true,
          );
          var anchorPos = editor.renderer.$cursorLayer.getPixelPosition(
            anchor,
            true,
          );
          var rect = editor.renderer.scroller.getBoundingClientRect();
          var offsetTop = editor.renderer.layerConfig.offset;
          var offsetLeft = editor.renderer.scrollLeft;
          var weightedDistance = function (x, y) {
            x = x / w;
            y = y / h - 0.75;
            return x * x + y * y;
          };
          if (e.clientX < rect.left) {
            mode = "zoom";
            return;
          }
          var diff1 = weightedDistance(
            e.clientX - rect.left - cursorPos.left + offsetLeft,
            e.clientY - rect.top - cursorPos.top + offsetTop,
          );
          var diff2 = weightedDistance(
            e.clientX - rect.left - anchorPos.left + offsetLeft,
            e.clientY - rect.top - anchorPos.top + offsetTop,
          );
          if (diff1 < 3.5 && diff2 < 3.5)
            mode = diff1 > diff2 ? "cursor" : "anchor";
          if (diff2 < 3.5) mode = "anchor";
          else if (diff1 < 3.5) mode = "cursor";
          else mode = "scroll";
          longTouchTimer = setTimeout(handleLongTap, 450);
        }
        touchStartT = t;
      },
      editor,
    );
    event.addListener(
      el,
      "touchend",
      function (e) {
        pressed = editor.$mouseHandler.isMousePressed = false;
        if (animationTimer) clearInterval(animationTimer);
        if (mode == "zoom") {
          mode = "";
          animationSteps = 0;
        } else if (longTouchTimer) {
          editor.selection.moveToPosition(pos);
          animationSteps = 0;
          showContextMenu();
        } else if (mode == "scroll") {
          animate();
          hideContextMenu();
        } else {
          showContextMenu();
        }
        clearTimeout(longTouchTimer);
        longTouchTimer = null;
      },
      editor,
    );
    event.addListener(
      el,
      "touchmove",
      function (e) {
        if (longTouchTimer) {
          clearTimeout(longTouchTimer);
          longTouchTimer = null;
        }
        var touches = e.touches;
        if (touches.length > 1 || mode == "zoom") return;
        var touchObj = touches[0];
        var wheelX = startX - touchObj.clientX;
        var wheelY = startY - touchObj.clientY;
        if (mode == "wait") {
          if (wheelX * wheelX + wheelY * wheelY > 4) mode = "cursor";
          else return e.preventDefault();
        }
        startX = touchObj.clientX;
        startY = touchObj.clientY;
        e.clientX = touchObj.clientX;
        e.clientY = touchObj.clientY;
        var t = e.timeStamp;
        var dt = t - lastT;
        lastT = t;
        if (mode == "scroll") {
          var mouseEvent = new MouseEvent(e, editor);
          mouseEvent.speed = 1;
          mouseEvent.wheelX = wheelX;
          mouseEvent.wheelY = wheelY;
          if (10 * Math.abs(wheelX) < Math.abs(wheelY)) wheelX = 0;
          if (10 * Math.abs(wheelY) < Math.abs(wheelX)) wheelY = 0;
          if (dt != 0) {
            vX = wheelX / dt;
            vY = wheelY / dt;
          }
          editor._emit("mousewheel", mouseEvent);
          if (!mouseEvent.propagationStopped) {
            vX = vY = 0;
          }
        } else {
          var ev = new MouseEvent(e, editor);
          var pos = ev.getDocumentPosition();
          if (mode == "cursor") editor.selection.moveCursorToPosition(pos);
          else if (mode == "anchor")
            editor.selection.setSelectionAnchor(pos.row, pos.column);
          editor.renderer.scrollCursorIntoView(pos);
          e.preventDefault();
        }
      },
      editor,
    );
    function animate() {
      animationSteps += 60;
      animationTimer = setInterval(function () {
        if (animationSteps-- <= 0) {
          clearInterval(animationTimer);
          animationTimer = null;
        }
        if (Math.abs(vX) < 0.01) vX = 0;
        if (Math.abs(vY) < 0.01) vY = 0;
        if (animationSteps < 20) vX = 0.9 * vX;
        if (animationSteps < 20) vY = 0.9 * vY;
        var oldScrollTop = editor.session.getScrollTop();
        editor.renderer.scrollBy(10 * vX, 10 * vY);
        if (oldScrollTop == editor.session.getScrollTop()) animationSteps = 0;
      }, 10);
    }
  };
});

define("ace/mouse/mouse_handler", [
  "require",
  "exports",
  "module",
  "ace/lib/event",
  "ace/lib/useragent",
  "ace/mouse/default_handlers",
  "ace/mouse/default_gutter_handler",
  "ace/mouse/mouse_event",
  "ace/mouse/dragdrop_handler",
  "ace/mouse/touch_handler",
  "ace/config",
], function (require, exports, module) {
  "use strict";
  var event = require("../lib/event");
  var useragent = require("../lib/useragent");
  var DefaultHandlers = require("./default_handlers").DefaultHandlers;
  var DefaultGutterHandler = require("./default_gutter_handler").GutterHandler;
  var MouseEvent = require("./mouse_event").MouseEvent;
  var DragdropHandler = require("./dragdrop_handler").DragdropHandler;
  var addTouchListeners = require("./touch_handler").addTouchListeners;
  var config = require("../config");
  var MouseHandler = /** @class */ (function () {
    function MouseHandler(editor) {
      this.$dragDelay;
      this.$dragEnabled;
      this.$mouseMoved;
      this.mouseEvent;
      this.$focusTimeout;
      var _self = this;
      this.editor = editor;
      new DefaultHandlers(this);
      new DefaultGutterHandler(this);
      new DragdropHandler(this);
      var focusEditor = function (e) {
        var windowBlurred =
          !document.hasFocus ||
          !document.hasFocus() ||
          (!editor.isFocused() &&
            document.activeElement ==
              (editor.textInput && editor.textInput.getElement()));
        if (windowBlurred) window.focus();
        editor.focus();
        setTimeout(function () {
          if (!editor.isFocused()) editor.focus();
        });
      };
      var mouseTarget = editor.renderer.getMouseEventTarget();
      event.addListener(
        mouseTarget,
        "click",
        this.onMouseEvent.bind(this, "click"),
        editor,
      );
      event.addListener(
        mouseTarget,
        "mousemove",
        this.onMouseMove.bind(this, "mousemove"),
        editor,
      );
      event.addMultiMouseDownListener(
        [
          mouseTarget,
          editor.renderer.scrollBarV && editor.renderer.scrollBarV.inner,
          editor.renderer.scrollBarH && editor.renderer.scrollBarH.inner,
          editor.textInput && editor.textInput.getElement(),
        ].filter(Boolean),
        [400, 300, 250],
        this,
        "onMouseEvent",
        editor,
      );
      event.addMouseWheelListener(
        editor.container,
        this.onMouseWheel.bind(this, "mousewheel"),
        editor,
      );
      addTouchListeners(editor.container, editor);
      var gutterEl = editor.renderer.$gutter;
      event.addListener(
        gutterEl,
        "mousedown",
        this.onMouseEvent.bind(this, "guttermousedown"),
        editor,
      );
      event.addListener(
        gutterEl,
        "click",
        this.onMouseEvent.bind(this, "gutterclick"),
        editor,
      );
      event.addListener(
        gutterEl,
        "dblclick",
        this.onMouseEvent.bind(this, "gutterdblclick"),
        editor,
      );
      event.addListener(
        gutterEl,
        "mousemove",
        this.onMouseEvent.bind(this, "guttermousemove"),
        editor,
      );
      event.addListener(mouseTarget, "mousedown", focusEditor, editor);
      event.addListener(gutterEl, "mousedown", focusEditor, editor);
      if (useragent.isIE && editor.renderer.scrollBarV) {
        event.addListener(
          editor.renderer.scrollBarV.element,
          "mousedown",
          focusEditor,
          editor,
        );
        event.addListener(
          editor.renderer.scrollBarH.element,
          "mousedown",
          focusEditor,
          editor,
        );
      }
      editor.on(
        "mousemove",
        function (e) {
          if (_self.state || _self.$dragDelay || !_self.$dragEnabled) return;
          var character = editor.renderer.screenToTextCoordinates(e.x, e.y);
          var range = editor.session.selection.getRange();
          var renderer = editor.renderer;
          if (
            !range.isEmpty() &&
            range.insideStart(character.row, character.column)
          ) {
            renderer.setCursorStyle("default");
          } else {
            renderer.setCursorStyle("");
          }
        }, //@ts-expect-error TODO: seems mistyping - should be boolean
        editor,
      );
    }
    MouseHandler.prototype.onMouseEvent = function (name, e) {
      if (!this.editor.session) return;
      this.editor._emit(name, new MouseEvent(e, this.editor));
    };
    MouseHandler.prototype.onMouseMove = function (name, e) {
      var listeners =
        this.editor._eventRegistry && this.editor._eventRegistry.mousemove;
      if (!listeners || !listeners.length) return;
      this.editor._emit(name, new MouseEvent(e, this.editor));
    };
    MouseHandler.prototype.onMouseWheel = function (name, e) {
      var mouseEvent = new MouseEvent(e, this.editor);
      mouseEvent.speed = this.$scrollSpeed * 2;
      mouseEvent.wheelX = e.wheelX;
      mouseEvent.wheelY = e.wheelY;
      this.editor._emit(name, mouseEvent);
    };
    MouseHandler.prototype.setState = function (state) {
      this.state = state;
    };
    MouseHandler.prototype.captureMouse = function (ev, mouseMoveHandler) {
      this.x = ev.x;
      this.y = ev.y;
      this.isMousePressed = true;
      var editor = this.editor;
      var renderer = this.editor.renderer;
      renderer.$isMousePressed = true;
      var self = this;
      var onMouseMove = function (e) {
        if (!e) return;
        if (useragent.isWebKit && !e.which && self.releaseMouse)
          return self.releaseMouse();
        self.x = e.clientX;
        self.y = e.clientY;
        mouseMoveHandler && mouseMoveHandler(e);
        self.mouseEvent = new MouseEvent(e, self.editor);
        self.$mouseMoved = true;
      };
      var onCaptureEnd = function (e) {
        editor.off("beforeEndOperation", onOperationEnd);
        clearInterval(timerId);
        if (editor.session) onCaptureInterval();
        self[self.state + "End"] && self[self.state + "End"](e);
        self.state = "";
        self.isMousePressed = renderer.$isMousePressed = false;
        if (renderer.$keepTextAreaAtCursor) renderer.$moveTextAreaToCursor();
        self.$onCaptureMouseMove = self.releaseMouse = null;
        e && self.onMouseEvent("mouseup", e);
        editor.endOperation();
      };
      var onCaptureInterval = function () {
        self[self.state] && self[self.state]();
        self.$mouseMoved = false;
      };
      if (useragent.isOldIE && ev.domEvent.type == "dblclick") {
        return setTimeout(function () {
          onCaptureEnd(ev);
        });
      }
      var onOperationEnd = function (e) {
        if (!self.releaseMouse) return;
        if (editor.curOp.command.name && editor.curOp.selectionChanged) {
          self[self.state + "End"] && self[self.state + "End"]();
          self.state = "";
          self.releaseMouse();
        }
      };
      editor.on("beforeEndOperation", onOperationEnd);
      editor.startOperation({ command: { name: "mouse" } });
      self.$onCaptureMouseMove = onMouseMove;
      self.releaseMouse = event.capture(
        this.editor.container,
        onMouseMove,
        onCaptureEnd,
      );
      var timerId = setInterval(onCaptureInterval, 20);
    };
    MouseHandler.prototype.cancelContextMenu = function () {
      var stop = function (e) {
        if (e && e.domEvent && e.domEvent.type != "contextmenu") return;
        this.editor.off("nativecontextmenu", stop);
        if (e && e.domEvent) event.stopEvent(e.domEvent);
      }.bind(this);
      setTimeout(stop, 10);
      this.editor.on("nativecontextmenu", stop);
    };
    MouseHandler.prototype.destroy = function () {
      if (this.releaseMouse) this.releaseMouse();
    };
    return MouseHandler;
  })();
  MouseHandler.prototype.releaseMouse = null;
  config.defineOptions(MouseHandler.prototype, "mouseHandler", {
    scrollSpeed: { initialValue: 2 },
    dragDelay: { initialValue: useragent.isMac ? 150 : 0 },
    dragEnabled: { initialValue: true },
    focusTimeout: { initialValue: 0 },
    tooltipFollowsMouse: { initialValue: true },
  });
  exports.MouseHandler = MouseHandler;
});

define("ace/mouse/fold_handler", [
  "require",
  "exports",
  "module",
  "ace/lib/dom",
], function (require, exports, module) {
  "use strict";
  var dom = require("../lib/dom");
  var FoldHandler = /** @class */ (function () {
    function FoldHandler(editor) {
      editor.on("click", function (e) {
        var position = e.getDocumentPosition();
        var session = editor.session;
        var fold = session.getFoldAt(position.row, position.column, 1);
        if (fold) {
          if (e.getAccelKey()) session.removeFold(fold);
          else session.expandFold(fold);
          e.stop();
        }
        var target = e.domEvent && e.domEvent.target;
        if (target && dom.hasCssClass(target, "ace_inline_button")) {
          if (dom.hasCssClass(target, "ace_toggle_wrap")) {
            session.setOption("wrap", !session.getUseWrapMode());
            editor.renderer.scrollCursorIntoView();
          }
        }
      });
      editor.on("gutterclick", function (e) {
        var gutterRegion = editor.renderer.$gutterLayer.getRegion(e);
        if (gutterRegion == "foldWidgets") {
          var row = e.getDocumentPosition().row;
          var session = editor.session;
          if (session.foldWidgets && session.foldWidgets[row])
            editor.session.onFoldWidgetClick(row, e);
          if (!editor.isFocused()) editor.focus();
          e.stop();
        }
      });
      editor.on("gutterdblclick", function (e) {
        var gutterRegion = editor.renderer.$gutterLayer.getRegion(e);
        if (gutterRegion == "foldWidgets") {
          var row = e.getDocumentPosition().row;
          var session = editor.session;
          var data = session.getParentFoldRangeData(row, true);
          var range = data.range || data.firstRange;
          if (range) {
            row = range.start.row;
            var fold = session.getFoldAt(row, session.getLine(row).length, 1);
            if (fold) {
              session.removeFold(fold);
            } else {
              session.addFold("...", range);
              editor.renderer.scrollCursorIntoView({
                row: range.start.row,
                column: 0,
              });
            }
          }
          e.stop();
        }
      });
    }
    return FoldHandler;
  })();
  exports.FoldHandler = FoldHandler;
});

define("ace/keyboard/keybinding", [
  "require",
  "exports",
  "module",
  "ace/lib/keys",
  "ace/lib/event",
], function (require, exports, module) {
  "use strict";
  var keyUtil = require("../lib/keys");
  var event = require("../lib/event");
  var KeyBinding = /** @class */ (function () {
    function KeyBinding(editor) {
      this.$editor = editor;
      this.$data = { editor: editor };
      this.$handlers = [];
      this.setDefaultHandler(editor.commands);
    }
    KeyBinding.prototype.setDefaultHandler = function (kb) {
      this.removeKeyboardHandler(this.$defaultHandler);
      this.$defaultHandler = kb;
      this.addKeyboardHandler(kb, 0);
    };
    KeyBinding.prototype.setKeyboardHandler = function (kb) {
      var h = this.$handlers;
      if (h[h.length - 1] == kb) return;
      while (h[h.length - 1] && h[h.length - 1] != this.$defaultHandler)
        this.removeKeyboardHandler(h[h.length - 1]);
      this.addKeyboardHandler(kb, 1);
    };
    KeyBinding.prototype.addKeyboardHandler = function (kb, pos) {
      if (!kb) return;
      if (typeof kb == "function" && !kb.handleKeyboard) kb.handleKeyboard = kb;
      var i = this.$handlers.indexOf(kb);
      if (i != -1) this.$handlers.splice(i, 1);
      if (pos == undefined) this.$handlers.push(kb);
      else this.$handlers.splice(pos, 0, kb);
      if (i == -1 && kb.attach) kb.attach(this.$editor);
    };
    KeyBinding.prototype.removeKeyboardHandler = function (kb) {
      var i = this.$handlers.indexOf(kb);
      if (i == -1) return false;
      this.$handlers.splice(i, 1);
      kb.detach && kb.detach(this.$editor);
      return true;
    };
    KeyBinding.prototype.getKeyboardHandler = function () {
      return this.$handlers[this.$handlers.length - 1];
    };
    KeyBinding.prototype.getStatusText = function () {
      var data = this.$data;
      var editor = data.editor;
      return this.$handlers
        .map(function (h) {
          return (h.getStatusText && h.getStatusText(editor, data)) || "";
        })
        .filter(Boolean)
        .join(" ");
    };
    KeyBinding.prototype.$callKeyboardHandlers = function (
      hashId,
      keyString,
      keyCode,
      e,
    ) {
      var toExecute;
      var success = false;
      var commands = this.$editor.commands;
      for (var i = this.$handlers.length; i--; ) {
        toExecute = this.$handlers[i].handleKeyboard(
          this.$data,
          hashId,
          keyString,
          keyCode,
          e,
        );
        if (!toExecute || !toExecute.command) continue;
        if (toExecute.command == "null") {
          success = true;
        } else {
          success = commands.exec(
            toExecute.command,
            this.$editor,
            toExecute.args,
            e,
          );
        }
        if (
          success &&
          e &&
          hashId != -1 &&
          toExecute["passEvent"] != true &&
          toExecute.command["passEvent"] != true
        ) {
          event.stopEvent(e);
        }
        if (success) break;
      }
      if (!success && hashId == -1) {
        toExecute = { command: "insertstring" };
        success = commands.exec("insertstring", this.$editor, keyString);
      }
      if (success && this.$editor._signal)
        this.$editor._signal("keyboardActivity", toExecute);
      return success;
    };
    KeyBinding.prototype.onCommandKey = function (e, hashId, keyCode) {
      var keyString = keyUtil.keyCodeToString(keyCode);
      return this.$callKeyboardHandlers(hashId, keyString, keyCode, e);
    };
    KeyBinding.prototype.onTextInput = function (text) {
      return this.$callKeyboardHandlers(-1, text);
    };
    return KeyBinding;
  })();
  exports.KeyBinding = KeyBinding;
});

define("ace/lib/bidiutil", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  "use strict";
  var ArabicAlefBetIntervalsBegine = ["\u0621", "\u0641"];
  var ArabicAlefBetIntervalsEnd = ["\u063A", "\u064a"];
  var dir = 0,
    hiLevel = 0;
  var lastArabic = false,
    hasUBAT_AL = false,
    hasUBAT_B = false,
    hasUBAT_S = false,
    hasBlockSep = false,
    hasSegSep = false;
  var impTab_LTR = [
    [0, 3, 0, 1, 0, 0, 0],
    [0, 3, 0, 1, 2, 2, 0],
    [0, 3, 0, 0x11, 2, 0, 1],
    [0, 3, 5, 5, 4, 1, 0],
    [0, 3, 0x15, 0x15, 4, 0, 1],
    [0, 3, 5, 5, 4, 2, 0],
  ];
  var impTab_RTL = [
    [2, 0, 1, 1, 0, 1, 0],
    [2, 0, 1, 1, 0, 2, 0],
    [2, 0, 2, 1, 3, 2, 0],
    [2, 0, 2, 0x21, 3, 1, 1],
  ];
  var LTR = 0,
    RTL = 1;
  var L = 0;
  var R = 1;
  var EN = 2;
  var AN = 3;
  var ON = 4;
  var B = 5;
  var S = 6;
  var AL = 7;
  var WS = 8;
  var CS = 9;
  var ES = 10;
  var ET = 11;
  var NSM = 12;
  var LRE = 13;
  var RLE = 14;
  var PDF = 15;
  var LRO = 16;
  var RLO = 17;
  var BN = 18;
  var UnicodeTBL00 = [
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    S,
    B,
    S,
    WS,
    B,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    B,
    B,
    B,
    S,
    WS,
    ON,
    ON,
    ET,
    ET,
    ET,
    ON,
    ON,
    ON,
    ON,
    ON,
    ES,
    CS,
    ES,
    CS,
    CS,
    EN,
    EN,
    EN,
    EN,
    EN,
    EN,
    EN,
    EN,
    EN,
    EN,
    CS,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    L,
    ON,
    ON,
    ON,
    ON,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    B,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    BN,
    CS,
    ON,
    ET,
    ET,
    ET,
    ET,
    ON,
    ON,
    ON,
    ON,
    L,
    ON,
    ON,
    BN,
    ON,
    ON,
    ET,
    ET,
    EN,
    EN,
    ON,
    L,
    ON,
    ON,
    ON,
    EN,
    L,
    ON,
    ON,
    ON,
    ON,
    ON,
  ];
  var UnicodeTBL20 = [
    WS,
    WS,
    WS,
    WS,
    WS,
    WS,
    WS,
    WS,
    WS,
    WS,
    WS,
    BN,
    BN,
    BN,
    L,
    R,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    WS,
    B,
    LRE,
    RLE,
    PDF,
    LRO,
    RLO,
    CS,
    ET,
    ET,
    ET,
    ET,
    ET,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    CS,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    ON,
    WS,
  ];
  function _computeLevels(chars, levels, len, charTypes) {
    var impTab = dir ? impTab_RTL : impTab_LTR,
      prevState = null,
      newClass = null,
      newLevel = null,
      newState = 0,
      action = null,
      cond = null,
      condPos = -1,
      i = null,
      ix = null,
      classes = [];
    if (!charTypes) {
      for (i = 0, charTypes = []; i < len; i++) {
        charTypes[i] = _getCharacterType(chars[i]);
      }
    }
    hiLevel = dir;
    lastArabic = false;
    hasUBAT_AL = false;
    hasUBAT_B = false;
    hasUBAT_S = false;
    for (ix = 0; ix < len; ix++) {
      prevState = newState;
      classes[ix] = newClass = _getCharClass(chars, charTypes, classes, ix);
      newState = impTab[prevState][newClass];
      action = newState & 0xf0;
      newState &= 0x0f;
      levels[ix] = newLevel = impTab[newState][5];
      if (action > 0) {
        if (action == 0x10) {
          for (i = condPos; i < ix; i++) {
            levels[i] = 1;
          }
          condPos = -1;
        } else {
          condPos = -1;
        }
      }
      cond = impTab[newState][6];
      if (cond) {
        if (condPos == -1) {
          condPos = ix;
        }
      } else {
        if (condPos > -1) {
          for (i = condPos; i < ix; i++) {
            levels[i] = newLevel;
          }
          condPos = -1;
        }
      }
      if (charTypes[ix] == B) {
        levels[ix] = 0;
      }
      hiLevel |= newLevel;
    }
    if (hasUBAT_S) {
      for (i = 0; i < len; i++) {
        if (charTypes[i] == S) {
          levels[i] = dir;
          for (var j = i - 1; j >= 0; j--) {
            if (charTypes[j] == WS) {
              levels[j] = dir;
            } else {
              break;
            }
          }
        }
      }
    }
  }
  function _invertLevel(lev, levels, _array) {
    if (hiLevel < lev) {
      return;
    }
    if (lev == 1 && dir == RTL && !hasUBAT_B) {
      _array.reverse();
      return;
    }
    var len = _array.length,
      start = 0,
      end,
      lo,
      hi,
      tmp;
    while (start < len) {
      if (levels[start] >= lev) {
        end = start + 1;
        while (end < len && levels[end] >= lev) {
          end++;
        }
        for (lo = start, hi = end - 1; lo < hi; lo++, hi--) {
          tmp = _array[lo];
          _array[lo] = _array[hi];
          _array[hi] = tmp;
        }
        start = end;
      }
      start++;
    }
  }
  function _getCharClass(chars, types, classes, ix) {
    var cType = types[ix],
      wType,
      nType,
      len,
      i;
    switch (cType) {
      case L:
      case R:
        lastArabic = false;
      case ON:
      case AN:
        return cType;
      case EN:
        return lastArabic ? AN : EN;
      case AL:
        lastArabic = true;
        hasUBAT_AL = true;
        return R;
      case WS:
        return ON;
      case CS:
        if (
          ix < 1 ||
          ix + 1 >= types.length ||
          ((wType = classes[ix - 1]) != EN && wType != AN) ||
          ((nType = types[ix + 1]) != EN && nType != AN)
        ) {
          return ON;
        }
        if (lastArabic) {
          nType = AN;
        }
        return nType == wType ? nType : ON;
      case ES:
        wType = ix > 0 ? classes[ix - 1] : B;
        if (wType == EN && ix + 1 < types.length && types[ix + 1] == EN) {
          return EN;
        }
        return ON;
      case ET:
        if (ix > 0 && classes[ix - 1] == EN) {
          return EN;
        }
        if (lastArabic) {
          return ON;
        }
        i = ix + 1;
        len = types.length;
        while (i < len && types[i] == ET) {
          i++;
        }
        if (i < len && types[i] == EN) {
          return EN;
        }
        return ON;
      case NSM:
        len = types.length;
        i = ix + 1;
        while (i < len && types[i] == NSM) {
          i++;
        }
        if (i < len) {
          var c = chars[ix],
            rtlCandidate = (c >= 0x0591 && c <= 0x08ff) || c == 0xfb1e;
          wType = types[i];
          if (rtlCandidate && (wType == R || wType == AL)) {
            return R;
          }
        }
        if (ix < 1 || (wType = types[ix - 1]) == B) {
          return ON;
        }
        return classes[ix - 1];
      case B:
        lastArabic = false;
        hasUBAT_B = true;
        return dir;
      case S:
        hasUBAT_S = true;
        return ON;
      case LRE:
      case RLE:
      case LRO:
      case RLO:
      case PDF:
        lastArabic = false;
      case BN:
        return ON;
    }
  }
  function _getCharacterType(ch) {
    var uc = ch.charCodeAt(0),
      hi = uc >> 8;
    if (hi == 0) {
      return uc > 0x00bf ? L : UnicodeTBL00[uc];
    } else if (hi == 5) {
      return /[\u0591-\u05f4]/.test(ch) ? R : L;
    } else if (hi == 6) {
      if (/[\u0610-\u061a\u064b-\u065f\u06d6-\u06e4\u06e7-\u06ed]/.test(ch))
        return NSM;
      else if (/[\u0660-\u0669\u066b-\u066c]/.test(ch)) return AN;
      else if (uc == 0x066a) return ET;
      else if (/[\u06f0-\u06f9]/.test(ch)) return EN;
      else return AL;
    } else if (hi == 0x20 && uc <= 0x205f) {
      return UnicodeTBL20[uc & 0xff];
    } else if (hi == 0xfe) {
      return uc >= 0xfe70 ? AL : ON;
    }
    return ON;
  }
  function _isArabicDiacritics(ch) {
    return ch >= "\u064b" && ch <= "\u0655";
  }
  exports.L = L;
  exports.R = R;
  exports.EN = EN;
  exports.ON_R = 3;
  exports.AN = 4;
  exports.R_H = 5;
  exports.B = 6;
  exports.RLE = 7;
  exports.DOT = "\xB7";
  exports.doBidiReorder = function (text, textCharTypes, isRtl) {
    if (text.length < 2) return {};
    var chars = text.split(""),
      logicalFromVisual = new Array(chars.length),
      bidiLevels = new Array(chars.length),
      levels = [];
    dir = isRtl ? RTL : LTR;
    _computeLevels(chars, levels, chars.length, textCharTypes);
    for (
      var i = 0;
      i < logicalFromVisual.length;
      logicalFromVisual[i] = i, i++
    );
    _invertLevel(2, levels, logicalFromVisual);
    _invertLevel(1, levels, logicalFromVisual);
    for (var i = 0; i < logicalFromVisual.length - 1; i++) {
      //fix levels to reflect character width
      if (textCharTypes[i] === AN) {
        levels[i] = exports.AN;
      } else if (
        levels[i] === R &&
        ((textCharTypes[i] > AL && textCharTypes[i] < LRE) ||
          textCharTypes[i] === ON ||
          textCharTypes[i] === BN)
      ) {
        levels[i] = exports.ON_R;
      } else if (
        i > 0 &&
        chars[i - 1] === "\u0644" &&
        /\u0622|\u0623|\u0625|\u0627/.test(chars[i])
      ) {
        levels[i - 1] = levels[i] = exports.R_H;
        i++;
      }
    }
    if (chars[chars.length - 1] === exports.DOT)
      levels[chars.length - 1] = exports.B;
    if (chars[0] === "\u202B") levels[0] = exports.RLE;
    for (var i = 0; i < logicalFromVisual.length; i++) {
      bidiLevels[i] = levels[logicalFromVisual[i]];
    }
    return { logicalFromVisual: logicalFromVisual, bidiLevels: bidiLevels };
  };
  exports.hasBidiCharacters = function (text, textCharTypes) {
    var ret = false;
    for (var i = 0; i < text.length; i++) {
      textCharTypes[i] = _getCharacterType(text.charAt(i));
      if (
        !ret &&
        (textCharTypes[i] == R ||
          textCharTypes[i] == AL ||
          textCharTypes[i] == AN)
      )
        ret = true;
    }
    return ret;
  };
  exports.getVisualFromLogicalIdx = function (logIdx, rowMap) {
    for (var i = 0; i < rowMap.logicalFromVisual.length; i++) {
      if (rowMap.logicalFromVisual[i] == logIdx) return i;
    }
    return 0;
  };
});

define("ace/bidihandler", [
  "require",
  "exports",
  "module",
  "ace/lib/bidiutil",
  "ace/lib/lang",
], function (require, exports, module) {
  "use strict";
  var bidiUtil = require("./lib/bidiutil");
  var lang = require("./lib/lang");
  var bidiRE = /[\u0590-\u05f4\u0600-\u06ff\u0700-\u08ac\u202B]/;
  var BidiHandler = /** @class */ (function () {
    function BidiHandler(session) {
      this.session = session;
      this.bidiMap = {};
      this.currentRow = null;
      this.bidiUtil = bidiUtil;
      this.charWidths = [];
      this.EOL = "\xAC";
      this.showInvisibles = true;
      this.isRtlDir = false;
      this.$isRtl = false;
      this.line = "";
      this.wrapIndent = 0;
      this.EOF = "\xB6";
      this.RLE = "\u202B";
      this.contentWidth = 0;
      this.fontMetrics = null;
      this.rtlLineOffset = 0;
      this.wrapOffset = 0;
      this.isMoveLeftOperation = false;
      this.seenBidi = bidiRE.test(session.getValue());
    }
    BidiHandler.prototype.isBidiRow = function (screenRow, docRow, splitIndex) {
      if (!this.seenBidi) return false;
      if (screenRow !== this.currentRow) {
        this.currentRow = screenRow;
        this.updateRowLine(docRow, splitIndex);
        this.updateBidiMap();
      }
      return this.bidiMap.bidiLevels;
    };
    BidiHandler.prototype.onChange = function (delta) {
      if (!this.seenBidi) {
        if (delta.action == "insert" && bidiRE.test(delta.lines.join("\n"))) {
          this.seenBidi = true;
          this.currentRow = null;
        }
      } else {
        this.currentRow = null;
      }
    };
    BidiHandler.prototype.getDocumentRow = function () {
      var docRow = 0;
      var rowCache = this.session.$screenRowCache;
      if (rowCache.length) {
        var index = this.session.$getRowCacheIndex(rowCache, this.currentRow);
        if (index >= 0) docRow = this.session.$docRowCache[index];
      }
      return docRow;
    };
    BidiHandler.prototype.getSplitIndex = function () {
      var splitIndex = 0;
      var rowCache = this.session.$screenRowCache;
      if (rowCache.length) {
        var currentIndex,
          prevIndex = this.session.$getRowCacheIndex(rowCache, this.currentRow);
        while (this.currentRow - splitIndex > 0) {
          currentIndex = this.session.$getRowCacheIndex(
            rowCache,
            this.currentRow - splitIndex - 1,
          );
          if (currentIndex !== prevIndex) break;
          prevIndex = currentIndex;
          splitIndex++;
        }
      } else {
        splitIndex = this.currentRow;
      }
      return splitIndex;
    };
    BidiHandler.prototype.updateRowLine = function (docRow, splitIndex) {
      if (docRow === undefined) docRow = this.getDocumentRow();
      var isLastRow = docRow === this.session.getLength() - 1,
        endOfLine = isLastRow ? this.EOF : this.EOL;
      this.wrapIndent = 0;
      this.line = this.session.getLine(docRow);
      this.isRtlDir = this.$isRtl || this.line.charAt(0) === this.RLE;
      if (this.session.$useWrapMode) {
        var splits = this.session.$wrapData[docRow];
        if (splits) {
          if (splitIndex === undefined) splitIndex = this.getSplitIndex();
          if (splitIndex > 0 && splits.length) {
            this.wrapIndent = splits.indent;
            this.wrapOffset = this.wrapIndent * this.charWidths[bidiUtil.L];
            this.line =
              splitIndex < splits.length
                ? this.line.substring(
                    splits[splitIndex - 1],
                    splits[splitIndex],
                  )
                : this.line.substring(splits[splits.length - 1]);
          } else {
            this.line = this.line.substring(0, splits[splitIndex]);
          }
          if (splitIndex == splits.length) {
            this.line += this.showInvisibles ? endOfLine : bidiUtil.DOT;
          }
        }
      } else {
        this.line += this.showInvisibles ? endOfLine : bidiUtil.DOT;
      }
      var session = this.session,
        shift = 0,
        size;
      this.line = this.line.replace(
        /\t|[\u1100-\u2029, \u202F-\uFFE6]/g,
        function (ch, i) {
          if (ch === "\t" || session.isFullWidth(ch.charCodeAt(0))) {
            size = ch === "\t" ? session.getScreenTabSize(i + shift) : 2;
            shift += size - 1;
            return lang.stringRepeat(bidiUtil.DOT, size);
          }
          return ch;
        },
      );
      if (this.isRtlDir) {
        this.fontMetrics.$main.textContent =
          this.line.charAt(this.line.length - 1) == bidiUtil.DOT
            ? this.line.substr(0, this.line.length - 1)
            : this.line;
        this.rtlLineOffset =
          this.contentWidth -
          this.fontMetrics.$main.getBoundingClientRect().width;
      }
    };
    BidiHandler.prototype.updateBidiMap = function () {
      var textCharTypes = [];
      if (
        bidiUtil.hasBidiCharacters(this.line, textCharTypes) ||
        this.isRtlDir
      ) {
        this.bidiMap = bidiUtil.doBidiReorder(
          this.line,
          textCharTypes,
          this.isRtlDir,
        );
      } else {
        this.bidiMap = {};
      }
    };
    BidiHandler.prototype.markAsDirty = function () {
      this.currentRow = null;
    };
    BidiHandler.prototype.updateCharacterWidths = function (fontMetrics) {
      if (this.characterWidth === fontMetrics.$characterSize.width) return;
      this.fontMetrics = fontMetrics;
      var characterWidth = (this.characterWidth =
        fontMetrics.$characterSize.width);
      var bidiCharWidth = fontMetrics.$measureCharWidth("\u05d4");
      this.charWidths[bidiUtil.L] =
        this.charWidths[bidiUtil.EN] =
        this.charWidths[bidiUtil.ON_R] =
          characterWidth;
      this.charWidths[bidiUtil.R] = this.charWidths[bidiUtil.AN] =
        bidiCharWidth;
      this.charWidths[bidiUtil.R_H] = bidiCharWidth * 0.45;
      this.charWidths[bidiUtil.B] = this.charWidths[bidiUtil.RLE] = 0;
      this.currentRow = null;
    };
    BidiHandler.prototype.setShowInvisibles = function (showInvisibles) {
      this.showInvisibles = showInvisibles;
      this.currentRow = null;
    };
    BidiHandler.prototype.setEolChar = function (eolChar) {
      this.EOL = eolChar;
    };
    BidiHandler.prototype.setContentWidth = function (width) {
      this.contentWidth = width;
    };
    BidiHandler.prototype.isRtlLine = function (row) {
      if (this.$isRtl) return true;
      if (row != undefined)
        return this.session.getLine(row).charAt(0) == this.RLE;
      else return this.isRtlDir;
    };
    BidiHandler.prototype.setRtlDirection = function (editor, isRtlDir) {
      var cursor = editor.getCursorPosition();
      for (
        var row = editor.selection.getSelectionAnchor().row;
        row <= cursor.row;
        row++
      ) {
        if (
          !isRtlDir &&
          editor.session.getLine(row).charAt(0) ===
            editor.session.$bidiHandler.RLE
        )
          editor.session.doc.removeInLine(row, 0, 1);
        else if (
          isRtlDir &&
          editor.session.getLine(row).charAt(0) !==
            editor.session.$bidiHandler.RLE
        )
          editor.session.doc.insert(
            { column: 0, row: row },
            editor.session.$bidiHandler.RLE,
          );
      }
    };
    BidiHandler.prototype.getPosLeft = function (col) {
      col -= this.wrapIndent;
      var leftBoundary = this.line.charAt(0) === this.RLE ? 1 : 0;
      var logicalIdx =
        col > leftBoundary
          ? this.session.getOverwrite()
            ? col
            : col - 1
          : leftBoundary;
      var visualIdx = bidiUtil.getVisualFromLogicalIdx(
          logicalIdx,
          this.bidiMap,
        ),
        levels = this.bidiMap.bidiLevels,
        left = 0;
      if (
        !this.session.getOverwrite() &&
        col <= leftBoundary &&
        levels[visualIdx] % 2 !== 0
      )
        visualIdx++;
      for (var i = 0; i < visualIdx; i++) {
        left += this.charWidths[levels[i]];
      }
      if (
        !this.session.getOverwrite() &&
        col > leftBoundary &&
        levels[visualIdx] % 2 === 0
      )
        left += this.charWidths[levels[visualIdx]];
      if (this.wrapIndent)
        left += this.isRtlDir ? -1 * this.wrapOffset : this.wrapOffset;
      if (this.isRtlDir) left += this.rtlLineOffset;
      return left;
    };
    BidiHandler.prototype.getSelections = function (startCol, endCol) {
      var map = this.bidiMap,
        levels = map.bidiLevels,
        level,
        selections = [],
        offset = 0,
        selColMin = Math.min(startCol, endCol) - this.wrapIndent,
        selColMax = Math.max(startCol, endCol) - this.wrapIndent,
        isSelected = false,
        isSelectedPrev = false,
        selectionStart = 0;
      if (this.wrapIndent)
        offset += this.isRtlDir ? -1 * this.wrapOffset : this.wrapOffset;
      for (var logIdx, visIdx = 0; visIdx < levels.length; visIdx++) {
        logIdx = map.logicalFromVisual[visIdx];
        level = levels[visIdx];
        isSelected = logIdx >= selColMin && logIdx < selColMax;
        if (isSelected && !isSelectedPrev) {
          selectionStart = offset;
        } else if (!isSelected && isSelectedPrev) {
          selections.push({
            left: selectionStart,
            width: offset - selectionStart,
          });
        }
        offset += this.charWidths[level];
        isSelectedPrev = isSelected;
      }
      if (isSelected && visIdx === levels.length) {
        selections.push({
          left: selectionStart,
          width: offset - selectionStart,
        });
      }
      if (this.isRtlDir) {
        for (var i = 0; i < selections.length; i++) {
          selections[i].left += this.rtlLineOffset;
        }
      }
      return selections;
    };
    BidiHandler.prototype.offsetToCol = function (posX) {
      if (this.isRtlDir) posX -= this.rtlLineOffset;
      var logicalIdx = 0,
        posX = Math.max(posX, 0),
        offset = 0,
        visualIdx = 0,
        levels = this.bidiMap.bidiLevels,
        charWidth = this.charWidths[levels[visualIdx]];
      if (this.wrapIndent)
        posX -= this.isRtlDir ? -1 * this.wrapOffset : this.wrapOffset;
      while (posX > offset + charWidth / 2) {
        offset += charWidth;
        if (visualIdx === levels.length - 1) {
          charWidth = 0;
          break;
        }
        charWidth = this.charWidths[levels[++visualIdx]];
      }
      if (
        visualIdx > 0 &&
        levels[visualIdx - 1] % 2 !== 0 &&
        levels[visualIdx] % 2 === 0
      ) {
        if (posX < offset) visualIdx--;
        logicalIdx = this.bidiMap.logicalFromVisual[visualIdx];
      } else if (
        visualIdx > 0 &&
        levels[visualIdx - 1] % 2 === 0 &&
        levels[visualIdx] % 2 !== 0
      ) {
        logicalIdx =
          1 +
          (posX > offset
            ? this.bidiMap.logicalFromVisual[visualIdx]
            : this.bidiMap.logicalFromVisual[visualIdx - 1]);
      } else if (
        (this.isRtlDir &&
          visualIdx === levels.length - 1 &&
          charWidth === 0 &&
          levels[visualIdx - 1] % 2 === 0) ||
        (!this.isRtlDir && visualIdx === 0 && levels[visualIdx] % 2 !== 0)
      ) {
        logicalIdx = 1 + this.bidiMap.logicalFromVisual[visualIdx];
      } else {
        if (visualIdx > 0 && levels[visualIdx - 1] % 2 !== 0 && charWidth !== 0)
          visualIdx--;
        logicalIdx = this.bidiMap.logicalFromVisual[visualIdx];
      }
      if (logicalIdx === 0 && this.isRtlDir) logicalIdx++;
      return logicalIdx + this.wrapIndent;
    };
    return BidiHandler;
  })();
  exports.BidiHandler = BidiHandler;
});

define("ace/selection", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/lang",
  "ace/lib/event_emitter",
  "ace/range",
], function (require, exports, module) {
  "use strict";
  var oop = require("./lib/oop");
  var lang = require("./lib/lang");
  var EventEmitter = require("./lib/event_emitter").EventEmitter;
  var Range = require("./range").Range;
  var Selection = /** @class */ (function () {
    function Selection(session) {
      this.session = session;
      this.doc = session.getDocument();
      this.clearSelection();
      this.cursor = this.lead = this.doc.createAnchor(0, 0);
      this.anchor = this.doc.createAnchor(0, 0);
      this.$silent = false;
      var self = this;
      this.cursor.on("change", function (e) {
        self.$cursorChanged = true;
        if (!self.$silent) self._emit("changeCursor");
        if (!self.$isEmpty && !self.$silent) self._emit("changeSelection");
        if (!self.$keepDesiredColumnOnChange && e.old.column != e.value.column)
          self.$desiredColumn = null;
      });
      this.anchor.on("change", function () {
        self.$anchorChanged = true;
        if (!self.$isEmpty && !self.$silent) self._emit("changeSelection");
      });
    }
    Selection.prototype.isEmpty = function () {
      return (
        this.$isEmpty ||
        (this.anchor.row == this.lead.row &&
          this.anchor.column == this.lead.column)
      );
    };
    Selection.prototype.isMultiLine = function () {
      return !this.$isEmpty && this.anchor.row != this.cursor.row;
    };
    Selection.prototype.getCursor = function () {
      return this.lead.getPosition();
    };
    Selection.prototype.setAnchor = function (row, column) {
      this.$isEmpty = false;
      this.anchor.setPosition(row, column);
    };
    Selection.prototype.getAnchor = function () {
      if (this.$isEmpty) return this.getSelectionLead();
      return this.anchor.getPosition();
    };
    Selection.prototype.getSelectionLead = function () {
      return this.lead.getPosition();
    };
    Selection.prototype.isBackwards = function () {
      var anchor = this.anchor;
      var lead = this.lead;
      return (
        anchor.row > lead.row ||
        (anchor.row == lead.row && anchor.column > lead.column)
      );
    };
    Selection.prototype.getRange = function () {
      var anchor = this.anchor;
      var lead = this.lead;
      if (this.$isEmpty) return Range.fromPoints(lead, lead);
      return this.isBackwards()
        ? Range.fromPoints(lead, anchor)
        : Range.fromPoints(anchor, lead);
    };
    Selection.prototype.clearSelection = function () {
      if (!this.$isEmpty) {
        this.$isEmpty = true;
        this._emit("changeSelection");
      }
    };
    Selection.prototype.selectAll = function () {
      this.$setSelection(0, 0, Number.MAX_VALUE, Number.MAX_VALUE);
    };
    Selection.prototype.setRange = function (range, reverse) {
      var start = reverse ? range.end : range.start;
      var end = reverse ? range.start : range.end;
      this.$setSelection(start.row, start.column, end.row, end.column);
    };
    Selection.prototype.$setSelection = function (
      anchorRow,
      anchorColumn,
      cursorRow,
      cursorColumn,
    ) {
      if (this.$silent) return;
      var wasEmpty = this.$isEmpty;
      var wasMultiselect = this.inMultiSelectMode;
      this.$silent = true;
      this.$cursorChanged = this.$anchorChanged = false;
      this.anchor.setPosition(anchorRow, anchorColumn);
      this.cursor.setPosition(cursorRow, cursorColumn);
      this.$isEmpty = !Range.comparePoints(this.anchor, this.cursor);
      this.$silent = false;
      if (this.$cursorChanged) this._emit("changeCursor");
      if (
        this.$cursorChanged ||
        this.$anchorChanged ||
        wasEmpty != this.$isEmpty ||
        wasMultiselect
      )
        this._emit("changeSelection");
    };
    Selection.prototype.$moveSelection = function (mover) {
      var lead = this.lead;
      if (this.$isEmpty) this.setSelectionAnchor(lead.row, lead.column);
      mover.call(this);
    };
    Selection.prototype.selectTo = function (row, column) {
      this.$moveSelection(function () {
        this.moveCursorTo(row, column);
      });
    };
    Selection.prototype.selectToPosition = function (pos) {
      this.$moveSelection(function () {
        this.moveCursorToPosition(pos);
      });
    };
    Selection.prototype.moveTo = function (row, column) {
      this.clearSelection();
      this.moveCursorTo(row, column);
    };
    Selection.prototype.moveToPosition = function (pos) {
      this.clearSelection();
      this.moveCursorToPosition(pos);
    };
    Selection.prototype.selectUp = function () {
      this.$moveSelection(this.moveCursorUp);
    };
    Selection.prototype.selectDown = function () {
      this.$moveSelection(this.moveCursorDown);
    };
    Selection.prototype.selectRight = function () {
      this.$moveSelection(this.moveCursorRight);
    };
    Selection.prototype.selectLeft = function () {
      this.$moveSelection(this.moveCursorLeft);
    };
    Selection.prototype.selectLineStart = function () {
      this.$moveSelection(this.moveCursorLineStart);
    };
    Selection.prototype.selectLineEnd = function () {
      this.$moveSelection(this.moveCursorLineEnd);
    };
    Selection.prototype.selectFileEnd = function () {
      this.$moveSelection(this.moveCursorFileEnd);
    };
    Selection.prototype.selectFileStart = function () {
      this.$moveSelection(this.moveCursorFileStart);
    };
    Selection.prototype.selectWordRight = function () {
      this.$moveSelection(this.moveCursorWordRight);
    };
    Selection.prototype.selectWordLeft = function () {
      this.$moveSelection(this.moveCursorWordLeft);
    };
    Selection.prototype.getWordRange = function (row, column) {
      if (typeof column == "undefined") {
        var cursor = row || this.lead;
        row = cursor.row;
        column = cursor.column;
      }
      return this.session.getWordRange(row, column);
    };
    Selection.prototype.selectWord = function () {
      this.setSelectionRange(this.getWordRange());
    };
    Selection.prototype.selectAWord = function () {
      var cursor = this.getCursor();
      var range = this.session.getAWordRange(cursor.row, cursor.column);
      this.setSelectionRange(range);
    };
    Selection.prototype.getLineRange = function (row, excludeLastChar) {
      var rowStart = typeof row == "number" ? row : this.lead.row;
      var rowEnd;
      var foldLine = this.session.getFoldLine(rowStart);
      if (foldLine) {
        rowStart = foldLine.start.row;
        rowEnd = foldLine.end.row;
      } else {
        rowEnd = rowStart;
      }
      if (excludeLastChar === true)
        return new Range(
          rowStart,
          0,
          rowEnd,
          this.session.getLine(rowEnd).length,
        );
      else return new Range(rowStart, 0, rowEnd + 1, 0);
    };
    Selection.prototype.selectLine = function () {
      this.setSelectionRange(this.getLineRange());
    };
    Selection.prototype.moveCursorUp = function () {
      this.moveCursorBy(-1, 0);
    };
    Selection.prototype.moveCursorDown = function () {
      this.moveCursorBy(1, 0);
    };
    Selection.prototype.wouldMoveIntoSoftTab = function (
      cursor,
      tabSize,
      direction,
    ) {
      var start = cursor.column;
      var end = cursor.column + tabSize;
      if (direction < 0) {
        start = cursor.column - tabSize;
        end = cursor.column;
      }
      return (
        this.session.isTabStop(cursor) &&
        this.doc.getLine(cursor.row).slice(start, end).split(" ").length - 1 ==
          tabSize
      );
    };
    Selection.prototype.moveCursorLeft = function () {
      var cursor = this.lead.getPosition(),
        fold;
      if ((fold = this.session.getFoldAt(cursor.row, cursor.column, -1))) {
        this.moveCursorTo(fold.start.row, fold.start.column);
      } else if (cursor.column === 0) {
        if (cursor.row > 0) {
          this.moveCursorTo(
            cursor.row - 1,
            this.doc.getLine(cursor.row - 1).length,
          );
        }
      } else {
        var tabSize = this.session.getTabSize();
        if (
          this.wouldMoveIntoSoftTab(cursor, tabSize, -1) &&
          !this.session.getNavigateWithinSoftTabs()
        ) {
          this.moveCursorBy(0, -tabSize);
        } else {
          this.moveCursorBy(0, -1);
        }
      }
    };
    Selection.prototype.moveCursorRight = function () {
      var cursor = this.lead.getPosition(),
        fold;
      if ((fold = this.session.getFoldAt(cursor.row, cursor.column, 1))) {
        this.moveCursorTo(fold.end.row, fold.end.column);
      } else if (this.lead.column == this.doc.getLine(this.lead.row).length) {
        if (this.lead.row < this.doc.getLength() - 1) {
          this.moveCursorTo(this.lead.row + 1, 0);
        }
      } else {
        var tabSize = this.session.getTabSize();
        var cursor = this.lead;
        if (
          this.wouldMoveIntoSoftTab(cursor, tabSize, 1) &&
          !this.session.getNavigateWithinSoftTabs()
        ) {
          this.moveCursorBy(0, tabSize);
        } else {
          this.moveCursorBy(0, 1);
        }
      }
    };
    Selection.prototype.moveCursorLineStart = function () {
      var row = this.lead.row;
      var column = this.lead.column;
      var screenRow = this.session.documentToScreenRow(row, column);
      var firstColumnPosition = this.session.screenToDocumentPosition(
        screenRow,
        0,
      );
      var beforeCursor = this.session.getDisplayLine(
        row,
        null,
        firstColumnPosition.row,
        firstColumnPosition.column,
      );
      var leadingSpace = beforeCursor.match(/^\s*/);
      if (
        leadingSpace[0].length != column &&
        !this.session.$useEmacsStyleLineStart
      )
        firstColumnPosition.column += leadingSpace[0].length;
      this.moveCursorToPosition(firstColumnPosition);
    };
    Selection.prototype.moveCursorLineEnd = function () {
      var lead = this.lead;
      var lineEnd = this.session.getDocumentLastRowColumnPosition(
        lead.row,
        lead.column,
      );
      if (this.lead.column == lineEnd.column) {
        var line = this.session.getLine(lineEnd.row);
        if (lineEnd.column == line.length) {
          var textEnd = line.search(/\s+$/);
          if (textEnd > 0) lineEnd.column = textEnd;
        }
      }
      this.moveCursorTo(lineEnd.row, lineEnd.column);
    };
    Selection.prototype.moveCursorFileEnd = function () {
      var row = this.doc.getLength() - 1;
      var column = this.doc.getLine(row).length;
      this.moveCursorTo(row, column);
    };
    Selection.prototype.moveCursorFileStart = function () {
      this.moveCursorTo(0, 0);
    };
    Selection.prototype.moveCursorLongWordRight = function () {
      var row = this.lead.row;
      var column = this.lead.column;
      var line = this.doc.getLine(row);
      var rightOfCursor = line.substring(column);
      this.session.nonTokenRe.lastIndex = 0;
      this.session.tokenRe.lastIndex = 0;
      var fold = this.session.getFoldAt(row, column, 1);
      if (fold) {
        this.moveCursorTo(fold.end.row, fold.end.column);
        return;
      }
      if (this.session.nonTokenRe.exec(rightOfCursor)) {
        column += this.session.nonTokenRe.lastIndex;
        this.session.nonTokenRe.lastIndex = 0;
        rightOfCursor = line.substring(column);
      }
      if (column >= line.length) {
        this.moveCursorTo(row, line.length);
        this.moveCursorRight();
        if (row < this.doc.getLength() - 1) this.moveCursorWordRight();
        return;
      }
      if (this.session.tokenRe.exec(rightOfCursor)) {
        column += this.session.tokenRe.lastIndex;
        this.session.tokenRe.lastIndex = 0;
      }
      this.moveCursorTo(row, column);
    };
    Selection.prototype.moveCursorLongWordLeft = function () {
      var row = this.lead.row;
      var column = this.lead.column;
      var fold;
      if ((fold = this.session.getFoldAt(row, column, -1))) {
        this.moveCursorTo(fold.start.row, fold.start.column);
        return;
      }
      var str = this.session.getFoldStringAt(row, column, -1);
      if (str == null) {
        str = this.doc.getLine(row).substring(0, column);
      }
      var leftOfCursor = lang.stringReverse(str);
      this.session.nonTokenRe.lastIndex = 0;
      this.session.tokenRe.lastIndex = 0;
      if (this.session.nonTokenRe.exec(leftOfCursor)) {
        column -= this.session.nonTokenRe.lastIndex;
        leftOfCursor = leftOfCursor.slice(this.session.nonTokenRe.lastIndex);
        this.session.nonTokenRe.lastIndex = 0;
      }
      if (column <= 0) {
        this.moveCursorTo(row, 0);
        this.moveCursorLeft();
        if (row > 0) this.moveCursorWordLeft();
        return;
      }
      if (this.session.tokenRe.exec(leftOfCursor)) {
        column -= this.session.tokenRe.lastIndex;
        this.session.tokenRe.lastIndex = 0;
      }
      this.moveCursorTo(row, column);
    };
    Selection.prototype.$shortWordEndIndex = function (rightOfCursor) {
      var index = 0,
        ch;
      var whitespaceRe = /\s/;
      var tokenRe = this.session.tokenRe;
      tokenRe.lastIndex = 0;
      if (this.session.tokenRe.exec(rightOfCursor)) {
        index = this.session.tokenRe.lastIndex;
      } else {
        while ((ch = rightOfCursor[index]) && whitespaceRe.test(ch)) index++;
        if (index < 1) {
          tokenRe.lastIndex = 0;
          while ((ch = rightOfCursor[index]) && !tokenRe.test(ch)) {
            tokenRe.lastIndex = 0;
            index++;
            if (whitespaceRe.test(ch)) {
              if (index > 2) {
                index--;
                break;
              } else {
                while ((ch = rightOfCursor[index]) && whitespaceRe.test(ch))
                  index++;
                if (index > 2) break;
              }
            }
          }
        }
      }
      tokenRe.lastIndex = 0;
      return index;
    };
    Selection.prototype.moveCursorShortWordRight = function () {
      var row = this.lead.row;
      var column = this.lead.column;
      var line = this.doc.getLine(row);
      var rightOfCursor = line.substring(column);
      var fold = this.session.getFoldAt(row, column, 1);
      if (fold) return this.moveCursorTo(fold.end.row, fold.end.column);
      if (column == line.length) {
        var l = this.doc.getLength();
        do {
          row++;
          rightOfCursor = this.doc.getLine(row);
        } while (row < l && /^\s*$/.test(rightOfCursor));
        if (!/^\s+/.test(rightOfCursor)) rightOfCursor = "";
        column = 0;
      }
      var index = this.$shortWordEndIndex(rightOfCursor);
      this.moveCursorTo(row, column + index);
    };
    Selection.prototype.moveCursorShortWordLeft = function () {
      var row = this.lead.row;
      var column = this.lead.column;
      var fold;
      if ((fold = this.session.getFoldAt(row, column, -1)))
        return this.moveCursorTo(fold.start.row, fold.start.column);
      var line = this.session.getLine(row).substring(0, column);
      if (column === 0) {
        do {
          row--;
          line = this.doc.getLine(row);
        } while (row > 0 && /^\s*$/.test(line));
        column = line.length;
        if (!/\s+$/.test(line)) line = "";
      }
      var leftOfCursor = lang.stringReverse(line);
      var index = this.$shortWordEndIndex(leftOfCursor);
      return this.moveCursorTo(row, column - index);
    };
    Selection.prototype.moveCursorWordRight = function () {
      if (this.session.$selectLongWords) this.moveCursorLongWordRight();
      else this.moveCursorShortWordRight();
    };
    Selection.prototype.moveCursorWordLeft = function () {
      if (this.session.$selectLongWords) this.moveCursorLongWordLeft();
      else this.moveCursorShortWordLeft();
    };
    Selection.prototype.moveCursorBy = function (rows, chars) {
      var screenPos = this.session.documentToScreenPosition(
        this.lead.row,
        this.lead.column,
      );
      var offsetX;
      if (chars === 0) {
        if (rows !== 0) {
          if (
            this.session.$bidiHandler.isBidiRow(screenPos.row, this.lead.row)
          ) {
            offsetX = this.session.$bidiHandler.getPosLeft(screenPos.column);
            screenPos.column = Math.round(
              offsetX / this.session.$bidiHandler.charWidths[0],
            );
          } else {
            offsetX =
              screenPos.column * this.session.$bidiHandler.charWidths[0];
          }
        }
        if (this.$desiredColumn) screenPos.column = this.$desiredColumn;
        else this.$desiredColumn = screenPos.column;
      }
      if (
        rows != 0 &&
        this.session.lineWidgets &&
        this.session.lineWidgets[this.lead.row]
      ) {
        var widget = this.session.lineWidgets[this.lead.row];
        if (rows < 0) rows -= widget.rowsAbove || 0;
        else if (rows > 0) rows += widget.rowCount - (widget.rowsAbove || 0);
      }
      var docPos = this.session.screenToDocumentPosition(
        screenPos.row + rows,
        screenPos.column,
        offsetX,
      );
      if (
        rows !== 0 &&
        chars === 0 &&
        docPos.row === this.lead.row &&
        docPos.column === this.lead.column
      ) {
      }
      this.moveCursorTo(docPos.row, docPos.column + chars, chars === 0);
    };
    Selection.prototype.moveCursorToPosition = function (position) {
      this.moveCursorTo(position.row, position.column);
    };
    Selection.prototype.moveCursorTo = function (
      row,
      column,
      keepDesiredColumn,
    ) {
      var fold = this.session.getFoldAt(row, column, 1);
      if (fold) {
        row = fold.start.row;
        column = fold.start.column;
      }
      this.$keepDesiredColumnOnChange = true;
      var line = this.session.getLine(row);
      if (
        /[\uDC00-\uDFFF]/.test(line.charAt(column)) &&
        line.charAt(column - 1)
      ) {
        if (this.lead.row == row && this.lead.column == column + 1)
          column = column - 1;
        else column = column + 1;
      }
      this.lead.setPosition(row, column);
      this.$keepDesiredColumnOnChange = false;
      if (!keepDesiredColumn) this.$desiredColumn = null;
    };
    Selection.prototype.moveCursorToScreen = function (
      row,
      column,
      keepDesiredColumn,
    ) {
      var pos = this.session.screenToDocumentPosition(row, column);
      this.moveCursorTo(pos.row, pos.column, keepDesiredColumn);
    };
    Selection.prototype.detach = function () {
      this.lead.detach();
      this.anchor.detach();
    };
    Selection.prototype.fromOrientedRange = function (range) {
      this.setSelectionRange(range, range.cursor == range.start);
      this.$desiredColumn = range.desiredColumn || this.$desiredColumn;
    };
    Selection.prototype.toOrientedRange = function (range) {
      var r = this.getRange();
      if (range) {
        range.start.column = r.start.column;
        range.start.row = r.start.row;
        range.end.column = r.end.column;
        range.end.row = r.end.row;
      } else {
        range = r;
      }
      range.cursor = this.isBackwards() ? range.start : range.end;
      range.desiredColumn = this.$desiredColumn;
      return range;
    };
    Selection.prototype.getRangeOfMovements = function (func) {
      var start = this.getCursor();
      try {
        func(this);
        var end = this.getCursor();
        return Range.fromPoints(start, end);
      } catch (e) {
        return Range.fromPoints(start, start);
      } finally {
        this.moveCursorToPosition(start);
      }
    };
    Selection.prototype.toJSON = function () {
      if (this.rangeCount) {
        var data = this.ranges.map(function (r) {
          var r1 = r.clone();
          r1.isBackwards = r.cursor == r.start;
          return r1;
        });
      } else {
        var data = this.getRange();
        data.isBackwards = this.isBackwards();
      }
      return data;
    };
    Selection.prototype.fromJSON = function (data) {
      if (data.start == undefined) {
        if (this.rangeList && data.length > 1) {
          this.toSingleRange(data[0]);
          for (var i = data.length; i--; ) {
            var r = Range.fromPoints(data[i].start, data[i].end);
            if (data[i].isBackwards) r.cursor = r.start;
            this.addRange(r, true);
          }
          return;
        } else {
          data = data[0];
        }
      }
      if (this.rangeList) this.toSingleRange(data);
      this.setSelectionRange(data, data.isBackwards);
    };
    Selection.prototype.isEqual = function (data) {
      if ((data.length || this.rangeCount) && data.length != this.rangeCount)
        return false;
      if (!data.length || !this.ranges) return this.getRange().isEqual(data);
      for (var i = this.ranges.length; i--; ) {
        if (!this.ranges[i].isEqual(data[i])) return false;
      }
      return true;
    };
    return Selection;
  })();
  Selection.prototype.setSelectionAnchor = Selection.prototype.setAnchor;
  Selection.prototype.getSelectionAnchor = Selection.prototype.getAnchor;
  Selection.prototype.setSelectionRange = Selection.prototype.setRange;
  oop.implement(Selection.prototype, EventEmitter);
  exports.Selection = Selection;
});

define("ace/tokenizer", [
  "require",
  "exports",
  "module",
  "ace/lib/report_error",
], function (require, exports, module) {
  "use strict";
  var reportError = require("./lib/report_error").reportError;
  var MAX_TOKEN_COUNT = 2000;
  var Tokenizer = /** @class */ (function () {
    function Tokenizer(rules) {
      this.splitRegex;
      this.states = rules;
      this.regExps = {};
      this.matchMappings = {};
      for (var key in this.states) {
        var state = this.states[key];
        var ruleRegExps = [];
        var matchTotal = 0;
        var mapping = (this.matchMappings[key] = { defaultToken: "text" });
        var flag = "g";
        var splitterRurles = [];
        for (var i = 0; i < state.length; i++) {
          var rule = state[i];
          if (rule.defaultToken) mapping.defaultToken = rule.defaultToken;
          if (rule.caseInsensitive && flag.indexOf("i") === -1) flag += "i";
          if (rule.unicode && flag.indexOf("u") === -1) flag += "u";
          if (rule.regex == null) continue;
          if (rule.regex instanceof RegExp)
            rule.regex = rule.regex.toString().slice(1, -1);
          var adjustedregex = rule.regex;
          var matchcount =
            new RegExp("(?:(" + adjustedregex + ")|(.))").exec("a").length - 2;
          if (Array.isArray(rule.token)) {
            if (rule.token.length == 1 || matchcount == 1) {
              rule.token = rule.token[0];
            } else if (matchcount - 1 != rule.token.length) {
              this.reportError(
                "number of classes and regexp groups doesn't match",
                {
                  rule: rule,
                  groupCount: matchcount - 1,
                },
              );
              rule.token = rule.token[0];
            } else {
              rule.tokenArray = rule.token;
              rule.token = null;
              rule.onMatch = this.$arrayTokens;
            }
          } else if (typeof rule.token == "function" && !rule.onMatch) {
            if (matchcount > 1) rule.onMatch = this.$applyToken;
            else rule.onMatch = rule.token;
          }
          if (matchcount > 1) {
            if (/\\\d/.test(rule.regex)) {
              adjustedregex = rule.regex.replace(
                /\\([0-9]+)/g,
                function (match, digit) {
                  return "\\" + (parseInt(digit, 10) + matchTotal + 1);
                },
              );
            } else {
              matchcount = 1;
              adjustedregex = this.removeCapturingGroups(rule.regex);
            }
            if (!rule.splitRegex && typeof rule.token != "string")
              splitterRurles.push(rule); // flag will be known only at the very end
          }
          mapping[matchTotal] = i;
          matchTotal += matchcount;
          ruleRegExps.push(adjustedregex);
          if (!rule.onMatch) rule.onMatch = null;
        }
        if (!ruleRegExps.length) {
          mapping[0] = 0;
          ruleRegExps.push("$");
        }
        splitterRurles.forEach(function (rule) {
          rule.splitRegex = this.createSplitterRegexp(rule.regex, flag);
        }, this);
        this.regExps[key] = new RegExp(
          "(" + ruleRegExps.join(")|(") + ")|($)",
          flag,
        );
      }
    }
    Tokenizer.prototype.$setMaxTokenCount = function (m) {
      MAX_TOKEN_COUNT = m | 0;
    };
    Tokenizer.prototype.$applyToken = function (str) {
      var values = this.splitRegex.exec(str).slice(1);
      var types = this.token.apply(this, values);
      if (typeof types === "string") return [{ type: types, value: str }];
      var tokens = [];
      for (var i = 0, l = types.length; i < l; i++) {
        if (values[i])
          tokens[tokens.length] = {
            type: types[i],
            value: values[i],
          };
      }
      return tokens;
    };
    Tokenizer.prototype.$arrayTokens = function (str) {
      if (!str) return [];
      var values = this.splitRegex.exec(str);
      if (!values) return "text";
      var tokens = [];
      var types = this.tokenArray;
      for (var i = 0, l = types.length; i < l; i++) {
        if (values[i + 1])
          tokens[tokens.length] = {
            type: types[i],
            value: values[i + 1],
          };
      }
      return tokens;
    };
    Tokenizer.prototype.removeCapturingGroups = function (src) {
      var r = src.replace(
        /\\.|\[(?:\\.|[^\\\]])*|\(\?[:=!<]|(\()/g,
        function (x, y) {
          return y ? "(?:" : x;
        },
      );
      return r;
    };
    Tokenizer.prototype.createSplitterRegexp = function (src, flag) {
      if (src.indexOf("(?=") != -1) {
        var stack = 0;
        var inChClass = false;
        var lastCapture = {};
        src.replace(
          /(\\.)|(\((?:\?[=!])?)|(\))|([\[\]])/g,
          function (m, esc, parenOpen, parenClose, square, index) {
            if (inChClass) {
              inChClass = square != "]";
            } else if (square) {
              inChClass = true;
            } else if (parenClose) {
              if (stack == lastCapture.stack) {
                lastCapture.end = index + 1;
                lastCapture.stack = -1;
              }
              stack--;
            } else if (parenOpen) {
              stack++;
              if (parenOpen.length != 1) {
                lastCapture.stack = stack;
                lastCapture.start = index;
              }
            }
            return m;
          },
        );
        if (
          lastCapture.end != null &&
          /^\)*$/.test(src.substr(lastCapture.end))
        )
          src =
            src.substring(0, lastCapture.start) + src.substr(lastCapture.end);
      }
      if (src.charAt(0) != "^") src = "^" + src;
      if (src.charAt(src.length - 1) != "$") src += "$";
      return new RegExp(src, (flag || "").replace("g", ""));
    };
    Tokenizer.prototype.getLineTokens = function (line, startState) {
      if (startState && typeof startState != "string") {
        var stack = startState.slice(0);
        startState = stack[0];
        if (startState === "#tmp") {
          stack.shift();
          startState = stack.shift();
        }
      } else var stack = [];
      var currentState = /**@type{string}*/ (startState) || "start";
      var state = this.states[currentState];
      if (!state) {
        currentState = "start";
        state = this.states[currentState];
      }
      var mapping = this.matchMappings[currentState];
      var re = this.regExps[currentState];
      re.lastIndex = 0;
      var match,
        tokens = [];
      var lastIndex = 0;
      var matchAttempts = 0;
      var token = { type: null, value: "" };
      while ((match = re.exec(line))) {
        var type = mapping.defaultToken;
        var rule = null;
        var value = match[0];
        var index = re.lastIndex;
        if (index - value.length > lastIndex) {
          var skipped = line.substring(lastIndex, index - value.length);
          if (token.type == type) {
            token.value += skipped;
          } else {
            if (token.type) tokens.push(token);
            token = { type: type, value: skipped };
          }
        }
        for (var i = 0; i < match.length - 2; i++) {
          if (match[i + 1] === undefined) continue;
          rule = state[mapping[i]];
          if (rule.onMatch)
            type = rule.onMatch(value, currentState, stack, line);
          else type = rule.token;
          if (rule.next) {
            if (typeof rule.next == "string") {
              currentState = rule.next;
            } else {
              currentState = rule.next(currentState, stack);
            }
            state = this.states[currentState];
            if (!state) {
              this.reportError("state doesn't exist", currentState);
              currentState = "start";
              state = this.states[currentState];
            }
            mapping = this.matchMappings[currentState];
            lastIndex = index;
            re = this.regExps[currentState];
            re.lastIndex = index;
          }
          if (rule.consumeLineEnd) lastIndex = index;
          break;
        }
        if (value) {
          if (typeof type === "string") {
            if ((!rule || rule.merge !== false) && token.type === type) {
              token.value += value;
            } else {
              if (token.type) tokens.push(token);
              token = { type: type, value: value };
            }
          } else if (type) {
            if (token.type) tokens.push(token);
            token = { type: null, value: "" };
            for (var i = 0; i < type.length; i++) tokens.push(type[i]);
          }
        }
        if (lastIndex == line.length) break;
        lastIndex = index;
        if (matchAttempts++ > MAX_TOKEN_COUNT) {
          if (matchAttempts > 2 * line.length) {
            this.reportError("infinite loop with in ace tokenizer", {
              startState: startState,
              line: line,
            });
          }
          while (lastIndex < line.length) {
            if (token.type) tokens.push(token);
            token = {
              value: line.substring(lastIndex, (lastIndex += 500)),
              type: "overflow",
            };
          }
          currentState = "start";
          stack = [];
          break;
        }
      }
      if (token.type) tokens.push(token);
      if (stack.length > 1) {
        if (stack[0] !== currentState) stack.unshift("#tmp", currentState);
      }
      return {
        tokens: tokens,
        state: stack.length ? stack : currentState,
      };
    };
    return Tokenizer;
  })();
  Tokenizer.prototype.reportError = reportError;
  exports.Tokenizer = Tokenizer;
});

define("ace/mode/text_highlight_rules", [
  "require",
  "exports",
  "module",
  "ace/lib/deep_copy",
], function (require, exports, module) {
  "use strict";
  var deepCopy = require("../lib/deep_copy").deepCopy;
  var TextHighlightRules;
  TextHighlightRules = function () {
    this.$rules = {
      start: [
        {
          token: "empty_line",
          regex: "^$",
        },
        {
          defaultToken: "text",
        },
      ],
    };
  };
  (function () {
    this.addRules = function (rules, prefix) {
      if (!prefix) {
        for (var key in rules) this.$rules[key] = rules[key];
        return;
      }
      for (var key in rules) {
        var state = rules[key];
        for (var i = 0; i < state.length; i++) {
          var rule = state[i];
          if (rule.next || rule.onMatch) {
            if (typeof rule.next == "string") {
              if (rule.next.indexOf(prefix) !== 0)
                rule.next = prefix + rule.next;
            }
            if (rule.nextState && rule.nextState.indexOf(prefix) !== 0)
              rule.nextState = prefix + rule.nextState;
          }
        }
        this.$rules[prefix + key] = state;
      }
    };
    this.getRules = function () {
      return this.$rules;
    };
    this.embedRules = function (
      HighlightRules,
      prefix,
      escapeRules,
      states,
      append,
    ) {
      var embedRules =
        typeof HighlightRules == "function"
          ? new HighlightRules().getRules()
          : HighlightRules;
      if (states) {
        for (var i = 0; i < states.length; i++) states[i] = prefix + states[i];
      } else {
        states = [];
        for (var key in embedRules) states.push(prefix + key);
      }
      this.addRules(embedRules, prefix);
      if (escapeRules) {
        var addRules = Array.prototype[append ? "push" : "unshift"];
        for (var i = 0; i < states.length; i++)
          addRules.apply(this.$rules[states[i]], deepCopy(escapeRules));
      }
      if (!this.$embeds) this.$embeds = [];
      this.$embeds.push(prefix);
    };
    this.getEmbeds = function () {
      return this.$embeds;
    };
    var pushState = function (currentState, stack) {
      if (currentState != "start" || stack.length)
        stack.unshift(this.nextState, currentState);
      return this.nextState;
    };
    var popState = function (currentState, stack) {
      stack.shift();
      return stack.shift() || "start";
    };
    this.normalizeRules = function () {
      var id = 0;
      var rules = this.$rules;
      function processState(key) {
        var state = rules[key];
        state["processed"] = true;
        for (var i = 0; i < state.length; i++) {
          var rule = state[i];
          var toInsert = null;
          if (Array.isArray(rule)) {
            toInsert = rule;
            rule = {};
          }
          if (!rule.regex && rule.start) {
            rule.regex = rule.start;
            if (!rule.next) rule.next = [];
            rule.next.push(
              {
                defaultToken: rule.token,
              },
              {
                token: rule.token + ".end",
                regex: rule.end || rule.start,
                next: "pop",
              },
            );
            rule.token = rule.token + ".start";
            rule.push = true;
          }
          var next = rule.next || rule.push;
          if (next && Array.isArray(next)) {
            var stateName = rule.stateName;
            if (!stateName) {
              stateName = rule.token;
              if (typeof stateName != "string") stateName = stateName[0] || "";
              if (rules[stateName]) stateName += id++;
            }
            rules[stateName] = next;
            rule.next = stateName;
            processState(stateName);
          } else if (next == "pop") {
            rule.next = popState;
          }
          if (rule.push) {
            rule.nextState = rule.next || rule.push;
            rule.next = pushState;
            delete rule.push;
          }
          if (rule.rules) {
            for (var r in rule.rules) {
              if (rules[r]) {
                if (rules[r].push) rules[r].push.apply(rules[r], rule.rules[r]);
              } else {
                rules[r] = rule.rules[r];
              }
            }
          }
          var includeName = typeof rule == "string" ? rule : rule.include;
          if (includeName) {
            if (includeName === "$self") includeName = "start";
            if (Array.isArray(includeName))
              toInsert = includeName.map(function (x) {
                return rules[x];
              });
            else toInsert = rules[includeName];
          }
          if (toInsert) {
            var args = [i, 1].concat(toInsert);
            if (rule.noEscape)
              args = args.filter(function (x) {
                return !x.next;
              });
            state.splice.apply(state, args);
            i--;
          }
          if (rule.keywordMap) {
            rule.token = this.createKeywordMapper(
              rule.keywordMap,
              rule.defaultToken || "text",
              rule.caseInsensitive,
            );
            delete rule.defaultToken;
          }
        }
      }
      Object.keys(rules).forEach(processState, this);
    };
    this.createKeywordMapper = function (
      map,
      defaultToken,
      ignoreCase,
      splitChar,
    ) {
      var keywords = Object.create(null);
      this.$keywordList = [];
      Object.keys(map).forEach(function (className) {
        var a = map[className];
        var list = a.split(splitChar || "|");
        for (var i = list.length; i--; ) {
          var word = list[i];
          this.$keywordList.push(word);
          if (ignoreCase) word = word.toLowerCase();
          keywords[word] = className;
        }
      }, this);
      map = null;
      return ignoreCase
        ? function (value) {
            return keywords[value.toLowerCase()] || defaultToken;
          }
        : function (value) {
            return keywords[value] || defaultToken;
          };
    };
    this.getKeywords = function () {
      return this.$keywords;
    };
  }).call(TextHighlightRules.prototype);
  exports.TextHighlightRules = TextHighlightRules;
});

define("ace/mode/behaviour", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  "use strict";
  var Behaviour;
  Behaviour = function () {
    this.$behaviours = {};
  };
  (function () {
    this.add = function (name, action, callback) {
      switch (undefined) {
        case this.$behaviours:
          this.$behaviours = {};
        case this.$behaviours[name]:
          this.$behaviours[name] = {};
      }
      this.$behaviours[name][action] = callback;
    };
    this.addBehaviours = function (behaviours) {
      for (var key in behaviours) {
        for (var action in behaviours[key]) {
          this.add(key, action, behaviours[key][action]);
        }
      }
    };
    this.remove = function (name) {
      if (this.$behaviours && this.$behaviours[name]) {
        delete this.$behaviours[name];
      }
    };
    this.inherit = function (mode, filter) {
      if (typeof mode === "function") {
        var behaviours = new mode().getBehaviours(filter);
      } else {
        var behaviours = mode.getBehaviours(filter);
      }
      this.addBehaviours(behaviours);
    };
    this.getBehaviours = function (filter) {
      if (!filter) {
        return this.$behaviours;
      } else {
        var ret = {};
        for (var i = 0; i < filter.length; i++) {
          if (this.$behaviours[filter[i]]) {
            ret[filter[i]] = this.$behaviours[filter[i]];
          }
        }
        return ret;
      }
    };
  }).call(Behaviour.prototype);
  exports.Behaviour = Behaviour;
});

define("ace/token_iterator", [
  "require",
  "exports",
  "module",
  "ace/range",
], function (require, exports, module) {
  "use strict";
  var Range = require("./range").Range;
  var TokenIterator = /** @class */ (function () {
    function TokenIterator(session, initialRow, initialColumn) {
      this.$session = session;
      this.$row = initialRow;
      this.$rowTokens = session.getTokens(initialRow);
      var token = session.getTokenAt(initialRow, initialColumn);
      this.$tokenIndex = token ? token.index : -1;
    }
    TokenIterator.prototype.stepBackward = function () {
      this.$tokenIndex -= 1;
      while (this.$tokenIndex < 0) {
        this.$row -= 1;
        if (this.$row < 0) {
          this.$row = 0;
          return null;
        }
        this.$rowTokens = this.$session.getTokens(this.$row);
        this.$tokenIndex = this.$rowTokens.length - 1;
      }
      return this.$rowTokens[this.$tokenIndex];
    };
    TokenIterator.prototype.stepForward = function () {
      this.$tokenIndex += 1;
      var rowCount;
      while (this.$tokenIndex >= this.$rowTokens.length) {
        this.$row += 1;
        if (!rowCount) rowCount = this.$session.getLength();
        if (this.$row >= rowCount) {
          this.$row = rowCount - 1;
          return null;
        }
        this.$rowTokens = this.$session.getTokens(this.$row);
        this.$tokenIndex = 0;
      }
      return this.$rowTokens[this.$tokenIndex];
    };
    TokenIterator.prototype.getCurrentToken = function () {
      return this.$rowTokens[this.$tokenIndex];
    };
    TokenIterator.prototype.getCurrentTokenRow = function () {
      return this.$row;
    };
    TokenIterator.prototype.getCurrentTokenColumn = function () {
      var rowTokens = this.$rowTokens;
      var tokenIndex = this.$tokenIndex;
      var column = rowTokens[tokenIndex].start;
      if (column !== undefined) return column;
      column = 0;
      while (tokenIndex > 0) {
        tokenIndex -= 1;
        column += rowTokens[tokenIndex].value.length;
      }
      return column;
    };
    TokenIterator.prototype.getCurrentTokenPosition = function () {
      return { row: this.$row, column: this.getCurrentTokenColumn() };
    };
    TokenIterator.prototype.getCurrentTokenRange = function () {
      var token = this.$rowTokens[this.$tokenIndex];
      var column = this.getCurrentTokenColumn();
      return new Range(
        this.$row,
        column,
        this.$row,
        column + token.value.length,
      );
    };
    return TokenIterator;
  })();
  exports.TokenIterator = TokenIterator;
});

define("ace/mode/behaviour/cstyle", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/mode/behaviour",
  "ace/token_iterator",
  "ace/lib/lang",
], function (require, exports, module) {
  "use strict";
  var oop = require("../../lib/oop");
  var Behaviour = require("../behaviour").Behaviour;
  var TokenIterator = require("../../token_iterator").TokenIterator;
  var lang = require("../../lib/lang");
  var SAFE_INSERT_IN_TOKENS = [
    "text",
    "paren.rparen",
    "rparen",
    "paren",
    "punctuation.operator",
  ];
  var SAFE_INSERT_BEFORE_TOKENS = [
    "text",
    "paren.rparen",
    "rparen",
    "paren",
    "punctuation.operator",
    "comment",
  ];
  var context;
  var contextCache = {};
  var defaultQuotes = { '"': '"', "'": "'" };
  var initContext = function (editor) {
    var id = -1;
    if (editor.multiSelect) {
      id = editor.selection.index;
      if (contextCache.rangeCount != editor.multiSelect.rangeCount)
        contextCache = { rangeCount: editor.multiSelect.rangeCount };
    }
    if (contextCache[id]) return (context = contextCache[id]);
    context = contextCache[id] = {
      autoInsertedBrackets: 0,
      autoInsertedRow: -1,
      autoInsertedLineEnd: "",
      maybeInsertedBrackets: 0,
      maybeInsertedRow: -1,
      maybeInsertedLineStart: "",
      maybeInsertedLineEnd: "",
    };
  };
  var getWrapped = function (selection, selected, opening, closing) {
    var rowDiff = selection.end.row - selection.start.row;
    return {
      text: opening + selected + closing,
      selection: [
        0,
        selection.start.column + 1,
        rowDiff,
        selection.end.column + (rowDiff ? 0 : 1),
      ],
    };
  };
  var CstyleBehaviour;
  CstyleBehaviour = function (options) {
    options = options || {};
    this.add(
      "braces",
      "insertion",
      function (state, action, editor, session, text) {
        var cursor = editor.getCursorPosition();
        var line = session.doc.getLine(cursor.row);
        if (text == "{") {
          initContext(editor);
          var selection = editor.getSelectionRange();
          var selected = session.doc.getTextRange(selection);
          if (
            selected !== "" &&
            selected !== "{" &&
            editor.getWrapBehavioursEnabled()
          ) {
            return getWrapped(selection, selected, "{", "}");
          } else if (CstyleBehaviour.isSaneInsertion(editor, session)) {
            if (
              /[\]\}\)]/.test(line[cursor.column]) ||
              editor.inMultiSelectMode ||
              options.braces
            ) {
              CstyleBehaviour.recordAutoInsert(editor, session, "}");
              return {
                text: "{}",
                selection: [1, 1],
              };
            } else {
              CstyleBehaviour.recordMaybeInsert(editor, session, "{");
              return {
                text: "{",
                selection: [1, 1],
              };
            }
          }
        } else if (text == "}") {
          initContext(editor);
          var rightChar = line.substring(cursor.column, cursor.column + 1);
          if (rightChar == "}") {
            var matching = session.$findOpeningBracket("}", {
              column: cursor.column + 1,
              row: cursor.row,
            });
            if (
              matching !== null &&
              CstyleBehaviour.isAutoInsertedClosing(cursor, line, text)
            ) {
              CstyleBehaviour.popAutoInsertedClosing();
              return {
                text: "",
                selection: [1, 1],
              };
            }
          }
        } else if (text == "\n" || text == "\r\n") {
          initContext(editor);
          var closing = "";
          if (CstyleBehaviour.isMaybeInsertedClosing(cursor, line)) {
            closing = lang.stringRepeat("}", context.maybeInsertedBrackets);
            CstyleBehaviour.clearMaybeInsertedClosing();
          }
          var rightChar = line.substring(cursor.column, cursor.column + 1);
          if (rightChar === "}") {
            var openBracePos = session.findMatchingBracket(
              { row: cursor.row, column: cursor.column + 1 },
              "}",
            );
            if (!openBracePos) return null;
            var next_indent = this.$getIndent(
              session.getLine(openBracePos.row),
            );
          } else if (closing) {
            var next_indent = this.$getIndent(line);
          } else {
            CstyleBehaviour.clearMaybeInsertedClosing();
            return;
          }
          var indent = next_indent + session.getTabString();
          return {
            text: "\n" + indent + "\n" + next_indent + closing,
            selection: [1, indent.length, 1, indent.length],
          };
        } else {
          CstyleBehaviour.clearMaybeInsertedClosing();
        }
      },
    );
    this.add(
      "braces",
      "deletion",
      function (state, action, editor, session, range) {
        var selected = session.doc.getTextRange(range);
        if (!range.isMultiLine() && selected == "{") {
          initContext(editor);
          var line = session.doc.getLine(range.start.row);
          var rightChar = line.substring(
            range.end.column,
            range.end.column + 1,
          );
          if (rightChar == "}") {
            range.end.column++;
            return range;
          } else {
            context.maybeInsertedBrackets--;
          }
        }
      },
    );
    this.add(
      "parens",
      "insertion",
      function (state, action, editor, session, text) {
        if (text == "(") {
          initContext(editor);
          var selection = editor.getSelectionRange();
          var selected = session.doc.getTextRange(selection);
          if (selected !== "" && editor.getWrapBehavioursEnabled()) {
            return getWrapped(selection, selected, "(", ")");
          } else if (CstyleBehaviour.isSaneInsertion(editor, session)) {
            CstyleBehaviour.recordAutoInsert(editor, session, ")");
            return {
              text: "()",
              selection: [1, 1],
            };
          }
        } else if (text == ")") {
          initContext(editor);
          var cursor = editor.getCursorPosition();
          var line = session.doc.getLine(cursor.row);
          var rightChar = line.substring(cursor.column, cursor.column + 1);
          if (rightChar == ")") {
            var matching = session.$findOpeningBracket(")", {
              column: cursor.column + 1,
              row: cursor.row,
            });
            if (
              matching !== null &&
              CstyleBehaviour.isAutoInsertedClosing(cursor, line, text)
            ) {
              CstyleBehaviour.popAutoInsertedClosing();
              return {
                text: "",
                selection: [1, 1],
              };
            }
          }
        }
      },
    );
    this.add(
      "parens",
      "deletion",
      function (state, action, editor, session, range) {
        var selected = session.doc.getTextRange(range);
        if (!range.isMultiLine() && selected == "(") {
          initContext(editor);
          var line = session.doc.getLine(range.start.row);
          var rightChar = line.substring(
            range.start.column + 1,
            range.start.column + 2,
          );
          if (rightChar == ")") {
            range.end.column++;
            return range;
          }
        }
      },
    );
    this.add(
      "brackets",
      "insertion",
      function (state, action, editor, session, text) {
        if (text == "[") {
          initContext(editor);
          var selection = editor.getSelectionRange();
          var selected = session.doc.getTextRange(selection);
          if (selected !== "" && editor.getWrapBehavioursEnabled()) {
            return getWrapped(selection, selected, "[", "]");
          } else if (CstyleBehaviour.isSaneInsertion(editor, session)) {
            CstyleBehaviour.recordAutoInsert(editor, session, "]");
            return {
              text: "[]",
              selection: [1, 1],
            };
          }
        } else if (text == "]") {
          initContext(editor);
          var cursor = editor.getCursorPosition();
          var line = session.doc.getLine(cursor.row);
          var rightChar = line.substring(cursor.column, cursor.column + 1);
          if (rightChar == "]") {
            var matching = session.$findOpeningBracket("]", {
              column: cursor.column + 1,
              row: cursor.row,
            });
            if (
              matching !== null &&
              CstyleBehaviour.isAutoInsertedClosing(cursor, line, text)
            ) {
              CstyleBehaviour.popAutoInsertedClosing();
              return {
                text: "",
                selection: [1, 1],
              };
            }
          }
        }
      },
    );
    this.add(
      "brackets",
      "deletion",
      function (state, action, editor, session, range) {
        var selected = session.doc.getTextRange(range);
        if (!range.isMultiLine() && selected == "[") {
          initContext(editor);
          var line = session.doc.getLine(range.start.row);
          var rightChar = line.substring(
            range.start.column + 1,
            range.start.column + 2,
          );
          if (rightChar == "]") {
            range.end.column++;
            return range;
          }
        }
      },
    );
    this.add(
      "string_dquotes",
      "insertion",
      function (state, action, editor, session, text) {
        var quotes = session.$mode.$quotes || defaultQuotes;
        if (text.length == 1 && quotes[text]) {
          if (
            this.lineCommentStart &&
            this.lineCommentStart.indexOf(text) != -1
          )
            return;
          initContext(editor);
          var quote = text;
          var selection = editor.getSelectionRange();
          var selected = session.doc.getTextRange(selection);
          if (
            selected !== "" &&
            (selected.length != 1 || !quotes[selected]) &&
            editor.getWrapBehavioursEnabled()
          ) {
            return getWrapped(selection, selected, quote, quote);
          } else if (!selected) {
            var cursor = editor.getCursorPosition();
            var line = session.doc.getLine(cursor.row);
            var leftChar = line.substring(cursor.column - 1, cursor.column);
            var rightChar = line.substring(cursor.column, cursor.column + 1);
            var token = session.getTokenAt(cursor.row, cursor.column);
            var rightToken = session.getTokenAt(cursor.row, cursor.column + 1);
            if (leftChar == "\\" && token && /escape/.test(token.type))
              return null;
            var stringBefore = token && /string|escape/.test(token.type);
            var stringAfter =
              !rightToken || /string|escape/.test(rightToken.type);
            var pair;
            if (rightChar == quote) {
              pair = stringBefore !== stringAfter;
              if (pair && /string\.end/.test(rightToken.type)) pair = false;
            } else {
              if (stringBefore && !stringAfter) return null; // wrap string with different quote
              if (stringBefore && stringAfter) return null; // do not pair quotes inside strings
              var wordRe = session.$mode.tokenRe;
              wordRe.lastIndex = 0;
              var isWordBefore = wordRe.test(leftChar);
              wordRe.lastIndex = 0;
              var isWordAfter = wordRe.test(rightChar);
              var pairQuotesAfter = session.$mode.$pairQuotesAfter;
              var shouldPairQuotes =
                pairQuotesAfter &&
                pairQuotesAfter[quote] &&
                pairQuotesAfter[quote].test(leftChar);
              if ((!shouldPairQuotes && isWordBefore) || isWordAfter)
                return null; // before or after alphanumeric
              if (rightChar && !/[\s;,.})\]\\]/.test(rightChar)) return null; // there is rightChar and it isn't closing
              var charBefore = line[cursor.column - 2];
              if (
                leftChar == quote &&
                (charBefore == quote || wordRe.test(charBefore))
              )
                return null;
              pair = true;
            }
            return {
              text: pair ? quote + quote : "",
              selection: [1, 1],
            };
          }
        }
      },
    );
    this.add(
      "string_dquotes",
      "deletion",
      function (state, action, editor, session, range) {
        var quotes = session.$mode.$quotes || defaultQuotes;
        var selected = session.doc.getTextRange(range);
        if (!range.isMultiLine() && quotes.hasOwnProperty(selected)) {
          initContext(editor);
          var line = session.doc.getLine(range.start.row);
          var rightChar = line.substring(
            range.start.column + 1,
            range.start.column + 2,
          );
          if (rightChar == selected) {
            range.end.column++;
            return range;
          }
        }
      },
    );
    if (options.closeDocComment !== false) {
      this.add(
        "doc comment end",
        "insertion",
        function (state, action, editor, session, text) {
          if (
            state === "doc-start" &&
            (text === "\n" || text === "\r\n") &&
            editor.selection.isEmpty()
          ) {
            var cursor = editor.getCursorPosition();
            var line = session.doc.getLine(cursor.row);
            var nextLine = session.doc.getLine(cursor.row + 1);
            var indent = this.$getIndent(line);
            if (/\s*\*/.test(nextLine)) {
              if (/^\s*\*/.test(line)) {
                return {
                  text: text + indent + "* ",
                  selection: [1, 3 + indent.length, 1, 3 + indent.length],
                };
              } else {
                return {
                  text: text + indent + " * ",
                  selection: [1, 3 + indent.length, 1, 3 + indent.length],
                };
              }
            }
            if (/\/\*\*/.test(line.substring(0, cursor.column))) {
              return {
                text: text + indent + " * " + text + " " + indent + "*/",
                selection: [1, 4 + indent.length, 1, 4 + indent.length],
              };
            }
          }
        },
      );
    }
  };
  CstyleBehaviour.isSaneInsertion = function (editor, session) {
    var cursor = editor.getCursorPosition();
    var iterator = new TokenIterator(session, cursor.row, cursor.column);
    if (
      !this.$matchTokenType(
        iterator.getCurrentToken() || "text",
        SAFE_INSERT_IN_TOKENS,
      )
    ) {
      if (/[)}\]]/.test(editor.session.getLine(cursor.row)[cursor.column]))
        return true;
      var iterator2 = new TokenIterator(session, cursor.row, cursor.column + 1);
      if (
        !this.$matchTokenType(
          iterator2.getCurrentToken() || "text",
          SAFE_INSERT_IN_TOKENS,
        )
      )
        return false;
    }
    iterator.stepForward();
    return (
      iterator.getCurrentTokenRow() !== cursor.row ||
      this.$matchTokenType(
        iterator.getCurrentToken() || "text",
        SAFE_INSERT_BEFORE_TOKENS,
      )
    );
  };
  CstyleBehaviour["$matchTokenType"] = function (token, types) {
    return types.indexOf(token.type || token) > -1;
  };
  CstyleBehaviour["recordAutoInsert"] = function (editor, session, bracket) {
    var cursor = editor.getCursorPosition();
    var line = session.doc.getLine(cursor.row);
    if (
      !this["isAutoInsertedClosing"](
        cursor,
        line,
        context.autoInsertedLineEnd[0],
      )
    )
      context.autoInsertedBrackets = 0;
    context.autoInsertedRow = cursor.row;
    context.autoInsertedLineEnd = bracket + line.substr(cursor.column);
    context.autoInsertedBrackets++;
  };
  CstyleBehaviour["recordMaybeInsert"] = function (editor, session, bracket) {
    var cursor = editor.getCursorPosition();
    var line = session.doc.getLine(cursor.row);
    if (!this["isMaybeInsertedClosing"](cursor, line))
      context.maybeInsertedBrackets = 0;
    context.maybeInsertedRow = cursor.row;
    context.maybeInsertedLineStart = line.substr(0, cursor.column) + bracket;
    context.maybeInsertedLineEnd = line.substr(cursor.column);
    context.maybeInsertedBrackets++;
  };
  CstyleBehaviour["isAutoInsertedClosing"] = function (cursor, line, bracket) {
    return (
      context.autoInsertedBrackets > 0 &&
      cursor.row === context.autoInsertedRow &&
      bracket === context.autoInsertedLineEnd[0] &&
      line.substr(cursor.column) === context.autoInsertedLineEnd
    );
  };
  CstyleBehaviour["isMaybeInsertedClosing"] = function (cursor, line) {
    return (
      context.maybeInsertedBrackets > 0 &&
      cursor.row === context.maybeInsertedRow &&
      line.substr(cursor.column) === context.maybeInsertedLineEnd &&
      line.substr(0, cursor.column) == context.maybeInsertedLineStart
    );
  };
  CstyleBehaviour["popAutoInsertedClosing"] = function () {
    context.autoInsertedLineEnd = context.autoInsertedLineEnd.substr(1);
    context.autoInsertedBrackets--;
  };
  CstyleBehaviour["clearMaybeInsertedClosing"] = function () {
    if (context) {
      context.maybeInsertedBrackets = 0;
      context.maybeInsertedRow = -1;
    }
  };
  oop.inherits(CstyleBehaviour, Behaviour);
  exports.CstyleBehaviour = CstyleBehaviour;
});

define("ace/unicode", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  "use strict";
  var wordChars = [
    48, 9, 8, 25, 5, 0, 2, 25, 48, 0, 11, 0, 5, 0, 6, 22, 2, 30, 2, 457, 5, 11,
    15, 4, 8, 0, 2, 0, 18, 116, 2, 1, 3, 3, 9, 0, 2, 2, 2, 0, 2, 19, 2, 82, 2,
    138, 2, 4, 3, 155, 12, 37, 3, 0, 8, 38, 10, 44, 2, 0, 2, 1, 2, 1, 2, 0, 9,
    26, 6, 2, 30, 10, 7, 61, 2, 9, 5, 101, 2, 7, 3, 9, 2, 18, 3, 0, 17, 58, 3,
    100, 15, 53, 5, 0, 6, 45, 211, 57, 3, 18, 2, 5, 3, 11, 3, 9, 2, 1, 7, 6, 2,
    2, 2, 7, 3, 1, 3, 21, 2, 6, 2, 0, 4, 3, 3, 8, 3, 1, 3, 3, 9, 0, 5, 1, 2, 4,
    3, 11, 16, 2, 2, 5, 5, 1, 3, 21, 2, 6, 2, 1, 2, 1, 2, 1, 3, 0, 2, 4, 5, 1,
    3, 2, 4, 0, 8, 3, 2, 0, 8, 15, 12, 2, 2, 8, 2, 2, 2, 21, 2, 6, 2, 1, 2, 4,
    3, 9, 2, 2, 2, 2, 3, 0, 16, 3, 3, 9, 18, 2, 2, 7, 3, 1, 3, 21, 2, 6, 2, 1,
    2, 4, 3, 8, 3, 1, 3, 2, 9, 1, 5, 1, 2, 4, 3, 9, 2, 0, 17, 1, 2, 5, 4, 2, 2,
    3, 4, 1, 2, 0, 2, 1, 4, 1, 4, 2, 4, 11, 5, 4, 4, 2, 2, 3, 3, 0, 7, 0, 15, 9,
    18, 2, 2, 7, 2, 2, 2, 22, 2, 9, 2, 4, 4, 7, 2, 2, 2, 3, 8, 1, 2, 1, 7, 3, 3,
    9, 19, 1, 2, 7, 2, 2, 2, 22, 2, 9, 2, 4, 3, 8, 2, 2, 2, 3, 8, 1, 8, 0, 2, 3,
    3, 9, 19, 1, 2, 7, 2, 2, 2, 22, 2, 15, 4, 7, 2, 2, 2, 3, 10, 0, 9, 3, 3, 9,
    11, 5, 3, 1, 2, 17, 4, 23, 2, 8, 2, 0, 3, 6, 4, 0, 5, 5, 2, 0, 2, 7, 19, 1,
    14, 57, 6, 14, 2, 9, 40, 1, 2, 0, 3, 1, 2, 0, 3, 0, 7, 3, 2, 6, 2, 2, 2, 0,
    2, 0, 3, 1, 2, 12, 2, 2, 3, 4, 2, 0, 2, 5, 3, 9, 3, 1, 35, 0, 24, 1, 7, 9,
    12, 0, 2, 0, 2, 0, 5, 9, 2, 35, 5, 19, 2, 5, 5, 7, 2, 35, 10, 0, 58, 73, 7,
    77, 3, 37, 11, 42, 2, 0, 4, 328, 2, 3, 3, 6, 2, 0, 2, 3, 3, 40, 2, 3, 3, 32,
    2, 3, 3, 6, 2, 0, 2, 3, 3, 14, 2, 56, 2, 3, 3, 66, 5, 0, 33, 15, 17, 84, 13,
    619, 3, 16, 2, 25, 6, 74, 22, 12, 2, 6, 12, 20, 12, 19, 13, 12, 2, 2, 2, 1,
    13, 51, 3, 29, 4, 0, 5, 1, 3, 9, 34, 2, 3, 9, 7, 87, 9, 42, 6, 69, 11, 28,
    4, 11, 5, 11, 11, 39, 3, 4, 12, 43, 5, 25, 7, 10, 38, 27, 5, 62, 2, 28, 3,
    10, 7, 9, 14, 0, 89, 75, 5, 9, 18, 8, 13, 42, 4, 11, 71, 55, 9, 9, 4, 48,
    83, 2, 2, 30, 14, 230, 23, 280, 3, 5, 3, 37, 3, 5, 3, 7, 2, 0, 2, 0, 2, 0,
    2, 30, 3, 52, 2, 6, 2, 0, 4, 2, 2, 6, 4, 3, 3, 5, 5, 12, 6, 2, 2, 6, 67, 1,
    20, 0, 29, 0, 14, 0, 17, 4, 60, 12, 5, 0, 4, 11, 18, 0, 5, 0, 3, 9, 2, 0, 4,
    4, 7, 0, 2, 0, 2, 0, 2, 3, 2, 10, 3, 3, 6, 4, 5, 0, 53, 1, 2684, 46, 2, 46,
    2, 132, 7, 6, 15, 37, 11, 53, 10, 0, 17, 22, 10, 6, 2, 6, 2, 6, 2, 6, 2, 6,
    2, 6, 2, 6, 2, 6, 2, 31, 48, 0, 470, 1, 36, 5, 2, 4, 6, 1, 5, 85, 3, 1, 3,
    2, 2, 89, 2, 3, 6, 40, 4, 93, 18, 23, 57, 15, 513, 6581, 75, 20939, 53,
    1164, 68, 45, 3, 268, 4, 27, 21, 31, 3, 13, 13, 1, 2, 24, 9, 69, 11, 1, 38,
    8, 3, 102, 3, 1, 111, 44, 25, 51, 13, 68, 12, 9, 7, 23, 4, 0, 5, 45, 3, 35,
    13, 28, 4, 64, 15, 10, 39, 54, 10, 13, 3, 9, 7, 22, 4, 1, 5, 66, 25, 2, 227,
    42, 2, 1, 3, 9, 7, 11171, 13, 22, 5, 48, 8453, 301, 3, 61, 3, 105, 39, 6,
    13, 4, 6, 11, 2, 12, 2, 4, 2, 0, 2, 1, 2, 1, 2, 107, 34, 362, 19, 63, 3, 53,
    41, 11, 5, 15, 17, 6, 13, 1, 25, 2, 33, 4, 2, 134, 20, 9, 8, 25, 5, 0, 2,
    25, 12, 88, 4, 5, 3, 5, 3, 5, 3, 2,
  ];
  var code = 0;
  var str = [];
  for (var i = 0; i < wordChars.length; i += 2) {
    str.push((code += wordChars[i]));
    if (wordChars[i + 1]) str.push(45, (code += wordChars[i + 1]));
  }
  exports.wordChars = String.fromCharCode.apply(null, str);
});

define("ace/mode/text", [
  "require",
  "exports",
  "module",
  "ace/config",
  "ace/tokenizer",
  "ace/mode/text_highlight_rules",
  "ace/mode/behaviour/cstyle",
  "ace/unicode",
  "ace/lib/lang",
  "ace/token_iterator",
  "ace/range",
], function (require, exports, module) {
  "use strict";
  var config = require("../config");
  var Tokenizer = require("../tokenizer").Tokenizer;
  var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;
  var CstyleBehaviour = require("./behaviour/cstyle").CstyleBehaviour;
  var unicode = require("../unicode");
  var lang = require("../lib/lang");
  var TokenIterator = require("../token_iterator").TokenIterator;
  var Range = require("../range").Range;
  var Mode;
  Mode = function () {
    this.HighlightRules = TextHighlightRules;
  };
  (function () {
    this.$defaultBehaviour = new CstyleBehaviour();
    this.tokenRe = new RegExp("^[" + unicode.wordChars + "\\$_]+", "g");
    this.nonTokenRe = new RegExp(
      "^(?:[^" + unicode.wordChars + "\\$_]|\\s])+",
      "g",
    );
    this.getTokenizer = function () {
      if (!this.$tokenizer) {
        this.$highlightRules =
          this.$highlightRules ||
          new this.HighlightRules(this.$highlightRuleConfig);
        this.$tokenizer = new Tokenizer(this.$highlightRules.getRules());
      }
      return this.$tokenizer;
    };
    this.lineCommentStart = "";
    this.blockComment = "";
    this.toggleCommentLines = function (state, session, startRow, endRow) {
      var doc = session.doc;
      var ignoreBlankLines = true;
      var shouldRemove = true;
      var minIndent = Infinity;
      var tabSize = session.getTabSize();
      var insertAtTabStop = false;
      if (!this.lineCommentStart) {
        if (!this.blockComment) return false;
        var lineCommentStart = this.blockComment.start;
        var lineCommentEnd = this.blockComment.end;
        var regexpStart = new RegExp(
          "^(\\s*)(?:" + lang.escapeRegExp(lineCommentStart) + ")",
        );
        var regexpEnd = new RegExp(
          "(?:" + lang.escapeRegExp(lineCommentEnd) + ")\\s*$",
        );
        var comment = function (line, i) {
          if (testRemove(line, i)) return;
          if (!ignoreBlankLines || /\S/.test(line)) {
            doc.insertInLine({ row: i, column: line.length }, lineCommentEnd);
            doc.insertInLine({ row: i, column: minIndent }, lineCommentStart);
          }
        };
        var uncomment = function (line, i) {
          var m;
          if ((m = line.match(regexpEnd)))
            doc.removeInLine(i, line.length - m[0].length, line.length);
          if ((m = line.match(regexpStart)))
            doc.removeInLine(i, m[1].length, m[0].length);
        };
        var testRemove = function (line, row) {
          if (regexpStart.test(line)) return true;
          var tokens = session.getTokens(row);
          for (var i = 0; i < tokens.length; i++) {
            if (tokens[i].type === "comment") return true;
          }
        };
      } else {
        if (Array.isArray(this.lineCommentStart)) {
          var regexpStart = this.lineCommentStart
            .map(lang.escapeRegExp)
            .join("|");
          var lineCommentStart = this.lineCommentStart[0];
        } else {
          var regexpStart = lang.escapeRegExp(this.lineCommentStart);
          var lineCommentStart = this.lineCommentStart;
        }
        regexpStart = new RegExp("^(\\s*)(?:" + regexpStart + ") ?");
        insertAtTabStop = session.getUseSoftTabs();
        var uncomment = function (line, i) {
          var m = line.match(regexpStart);
          if (!m) return;
          var start = m[1].length,
            end = m[0].length;
          if (!shouldInsertSpace(line, start, end) && m[0][end - 1] == " ")
            end--;
          doc.removeInLine(i, start, end);
        };
        var commentWithSpace = lineCommentStart + " ";
        var comment = function (line, i) {
          if (!ignoreBlankLines || /\S/.test(line)) {
            if (shouldInsertSpace(line, minIndent, minIndent))
              doc.insertInLine({ row: i, column: minIndent }, commentWithSpace);
            else
              doc.insertInLine({ row: i, column: minIndent }, lineCommentStart);
          }
        };
        var testRemove = function (line, i) {
          return regexpStart.test(line);
        };
        var shouldInsertSpace = function (line, before, after) {
          var spaces = 0;
          while (before-- && line.charAt(before) == " ") spaces++;
          if (spaces % tabSize != 0) return false;
          var spaces = 0;
          while (line.charAt(after++) == " ") spaces++;
          if (tabSize > 2) return spaces % tabSize != tabSize - 1;
          else return spaces % tabSize == 0;
        };
      }
      function iter(fun) {
        for (var i = startRow; i <= endRow; i++) fun(doc.getLine(i), i);
      }
      var minEmptyLength = Infinity;
      iter(function (line, i) {
        var indent = line.search(/\S/);
        if (indent !== -1) {
          if (indent < minIndent) minIndent = indent;
          if (shouldRemove && !testRemove(line, i)) shouldRemove = false;
        } else if (minEmptyLength > line.length) {
          minEmptyLength = line.length;
        }
      });
      if (minIndent == Infinity) {
        minIndent = minEmptyLength;
        ignoreBlankLines = false;
        shouldRemove = false;
      }
      if (insertAtTabStop && minIndent % tabSize != 0)
        minIndent = Math.floor(minIndent / tabSize) * tabSize;
      iter(shouldRemove ? uncomment : comment);
    };
    this.toggleBlockComment = function (state, session, range, cursor) {
      var comment = this.blockComment;
      if (!comment) return;
      if (!comment.start && comment[0]) comment = comment[0];
      var iterator = new TokenIterator(session, cursor.row, cursor.column);
      var token = iterator.getCurrentToken();
      var sel = session.selection;
      var initialRange = session.selection.toOrientedRange();
      var startRow, colDiff;
      if (token && /comment/.test(token.type)) {
        var startRange, endRange;
        while (token && /comment/.test(token.type)) {
          var i = token.value.indexOf(comment.start);
          if (i != -1) {
            var row = iterator.getCurrentTokenRow();
            var column = iterator.getCurrentTokenColumn() + i;
            startRange = new Range(
              row,
              column,
              row,
              column + comment.start.length,
            );
            break;
          }
          token = iterator.stepBackward();
        }
        var iterator = new TokenIterator(session, cursor.row, cursor.column);
        var token = iterator.getCurrentToken();
        while (token && /comment/.test(token.type)) {
          var i = token.value.indexOf(comment.end);
          if (i != -1) {
            var row = iterator.getCurrentTokenRow();
            var column = iterator.getCurrentTokenColumn() + i;
            endRange = new Range(row, column, row, column + comment.end.length);
            break;
          }
          token = iterator.stepForward();
        }
        if (endRange) session.remove(endRange);
        if (startRange) {
          session.remove(startRange);
          startRow = startRange.start.row;
          colDiff = -comment.start.length;
        }
      } else {
        colDiff = comment.start.length;
        startRow = range.start.row;
        session.insert(range.end, comment.end);
        session.insert(range.start, comment.start);
      }
      if (initialRange.start.row == startRow)
        initialRange.start.column += colDiff;
      if (initialRange.end.row == startRow) initialRange.end.column += colDiff;
      session.selection.fromOrientedRange(initialRange);
    };
    this.getNextLineIndent = function (state, line, tab) {
      return this.$getIndent(line);
    };
    this.checkOutdent = function (state, line, input) {
      return false;
    };
    this.autoOutdent = function (state, doc, row) {};
    this.$getIndent = function (line) {
      return line.match(/^\s*/)[0];
    };
    this.createWorker = function (session) {
      return null;
    };
    this.createModeDelegates = function (mapping) {
      this.$embeds = [];
      this.$modes = {};
      for (var i in mapping) {
        if (mapping[i]) {
          var Mode = mapping[i];
          var id = Mode.prototype.$id;
          var mode = config.$modes[id];
          if (!mode) config.$modes[id] = mode = new Mode();
          if (!config.$modes[i]) config.$modes[i] = mode;
          this.$embeds.push(i);
          this.$modes[i] = mode;
        }
      }
      var delegations = [
        "toggleBlockComment",
        "toggleCommentLines",
        "getNextLineIndent",
        "checkOutdent",
        "autoOutdent",
        "transformAction",
        "getCompletions",
      ];
      var _loop_1 = function (i) {
        (function (scope) {
          var functionName = delegations[i];
          var defaultHandler = scope[functionName];
          scope[delegations[i]] = function () {
            return this.$delegator(functionName, arguments, defaultHandler);
          };
        })(this_1);
      };
      var this_1 = this;
      for (var i = 0; i < delegations.length; i++) {
        _loop_1(i);
      }
    };
    this.$delegator = function (method, args, defaultHandler) {
      var state = args[0] || "start";
      if (typeof state != "string") {
        if (Array.isArray(state[2])) {
          var language = state[2][state[2].length - 1];
          var mode = this.$modes[language];
          if (mode)
            return mode[method].apply(
              mode,
              [state[1]].concat([].slice.call(args, 1)),
            );
        }
        state = state[0] || "start";
      }
      for (var i = 0; i < this.$embeds.length; i++) {
        if (!this.$modes[this.$embeds[i]]) continue;
        var split = state.split(this.$embeds[i]);
        if (!split[0] && split[1]) {
          args[0] = split[1];
          var mode = this.$modes[this.$embeds[i]];
          return mode[method].apply(mode, args);
        }
      }
      var ret = defaultHandler.apply(this, args);
      return defaultHandler ? ret : undefined;
    };
    this.transformAction = function (state, action, editor, session, param) {
      if (this.$behaviour) {
        var behaviours = this.$behaviour.getBehaviours();
        for (var key in behaviours) {
          if (behaviours[key][action]) {
            var ret = behaviours[key][action].apply(this, arguments);
            if (ret) {
              return ret;
            }
          }
        }
      }
    };
    this.getKeywords = function (append) {
      if (!this.completionKeywords) {
        var rules = this.$tokenizer["rules"];
        var completionKeywords = [];
        for (var rule in rules) {
          var ruleItr = rules[rule];
          for (var r = 0, l = ruleItr.length; r < l; r++) {
            if (typeof ruleItr[r].token === "string") {
              if (/keyword|support|storage/.test(ruleItr[r].token))
                completionKeywords.push(ruleItr[r].regex);
            } else if (typeof ruleItr[r].token === "object") {
              for (
                var a = 0, aLength = ruleItr[r].token.length;
                a < aLength;
                a++
              ) {
                if (/keyword|support|storage/.test(ruleItr[r].token[a])) {
                  var rule = ruleItr[r].regex.match(/\(.+?\)/g)[a];
                  completionKeywords.push(rule.substr(1, rule.length - 2));
                }
              }
            }
          }
        }
        this.completionKeywords = completionKeywords;
      }
      if (!append) return this.$keywordList;
      return completionKeywords.concat(this.$keywordList || []);
    };
    this.$createKeywordList = function () {
      if (!this.$highlightRules) this.getTokenizer();
      return (this.$keywordList = this.$highlightRules.$keywordList || []);
    };
    this.getCompletions = function (state, session, pos, prefix) {
      var keywords = this.$keywordList || this.$createKeywordList();
      return keywords.map(function (word) {
        return {
          name: word,
          value: word,
          score: 0,
          meta: "keyword",
        };
      });
    };
    this.$id = "ace/mode/text";
  }).call(Mode.prototype);
  exports.Mode = Mode;
});

define("ace/apply_delta", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  "use strict";
  function throwDeltaError(delta, errorText) {
    console.log("Invalid Delta:", delta);
    throw "Invalid Delta: " + errorText;
  }
  function positionInDocument(docLines, position) {
    return (
      position.row >= 0 &&
      position.row < docLines.length &&
      position.column >= 0 &&
      position.column <= docLines[position.row].length
    );
  }
  function validateDelta(docLines, delta) {
    if (delta.action != "insert" && delta.action != "remove")
      throwDeltaError(delta, "delta.action must be 'insert' or 'remove'");
    if (!(delta.lines instanceof Array))
      throwDeltaError(delta, "delta.lines must be an Array");
    if (!delta.start || !delta.end)
      throwDeltaError(delta, "delta.start/end must be an present");
    var start = delta.start;
    if (!positionInDocument(docLines, delta.start))
      throwDeltaError(delta, "delta.start must be contained in document");
    var end = delta.end;
    if (delta.action == "remove" && !positionInDocument(docLines, end))
      throwDeltaError(
        delta,
        "delta.end must contained in document for 'remove' actions",
      );
    var numRangeRows = end.row - start.row;
    var numRangeLastLineChars =
      end.column - (numRangeRows == 0 ? start.column : 0);
    if (
      numRangeRows != delta.lines.length - 1 ||
      delta.lines[numRangeRows].length != numRangeLastLineChars
    )
      throwDeltaError(delta, "delta.range must match delta lines");
  }
  exports.applyDelta = function (docLines, delta, doNotValidate) {
    var row = delta.start.row;
    var startColumn = delta.start.column;
    var line = docLines[row] || "";
    switch (delta.action) {
      case "insert":
        var lines = delta.lines;
        if (lines.length === 1) {
          docLines[row] =
            line.substring(0, startColumn) +
            delta.lines[0] +
            line.substring(startColumn);
        } else {
          var args = [row, 1].concat(delta.lines);
          docLines.splice.apply(docLines, args);
          docLines[row] = line.substring(0, startColumn) + docLines[row];
          docLines[row + delta.lines.length - 1] += line.substring(startColumn);
        }
        break;
      case "remove":
        var endColumn = delta.end.column;
        var endRow = delta.end.row;
        if (row === endRow) {
          docLines[row] =
            line.substring(0, startColumn) + line.substring(endColumn);
        } else {
          docLines.splice(
            row,
            endRow - row + 1,
            line.substring(0, startColumn) +
              docLines[endRow].substring(endColumn),
          );
        }
        break;
    }
  };
});

define("ace/anchor", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/event_emitter",
], function (require, exports, module) {
  "use strict";
  var oop = require("./lib/oop");
  var EventEmitter = require("./lib/event_emitter").EventEmitter;
  var Anchor = /** @class */ (function () {
    function Anchor(doc, row, column) {
      this.$onChange = this.onChange.bind(this);
      this.attach(doc);
      if (typeof row != "number") this.setPosition(row.row, row.column);
      else this.setPosition(row, column);
    }
    Anchor.prototype.getPosition = function () {
      return this.$clipPositionToDocument(this.row, this.column);
    };
    Anchor.prototype.getDocument = function () {
      return this.document;
    };
    Anchor.prototype.onChange = function (delta) {
      if (delta.start.row == delta.end.row && delta.start.row != this.row)
        return;
      if (delta.start.row > this.row) return;
      var point = $getTransformedPoint(
        delta,
        { row: this.row, column: this.column },
        this.$insertRight,
      );
      this.setPosition(point.row, point.column, true);
    };
    Anchor.prototype.setPosition = function (row, column, noClip) {
      var pos;
      if (noClip) {
        pos = {
          row: row,
          column: column,
        };
      } else {
        pos = this.$clipPositionToDocument(row, column);
      }
      if (this.row == pos.row && this.column == pos.column) return;
      var old = {
        row: this.row,
        column: this.column,
      };
      this.row = pos.row;
      this.column = pos.column;
      this._signal("change", {
        old: old,
        value: pos,
      });
    };
    Anchor.prototype.detach = function () {
      this.document.off("change", this.$onChange);
    };
    Anchor.prototype.attach = function (doc) {
      this.document = doc || this.document;
      this.document.on("change", this.$onChange);
    };
    Anchor.prototype.$clipPositionToDocument = function (row, column) {
      var pos = {};
      if (row >= this.document.getLength()) {
        pos.row = Math.max(0, this.document.getLength() - 1);
        pos.column = this.document.getLine(pos.row).length;
      } else if (row < 0) {
        pos.row = 0;
        pos.column = 0;
      } else {
        pos.row = row;
        pos.column = Math.min(
          this.document.getLine(pos.row).length,
          Math.max(0, column),
        );
      }
      if (column < 0) pos.column = 0;
      return pos;
    };
    return Anchor;
  })();
  Anchor.prototype.$insertRight = false;
  oop.implement(Anchor.prototype, EventEmitter);
  function $pointsInOrder(point1, point2, equalPointsInOrder) {
    var bColIsAfter = equalPointsInOrder
      ? point1.column <= point2.column
      : point1.column < point2.column;
    return point1.row < point2.row || (point1.row == point2.row && bColIsAfter);
  }
  function $getTransformedPoint(delta, point, moveIfEqual) {
    var deltaIsInsert = delta.action == "insert";
    var deltaRowShift =
      (deltaIsInsert ? 1 : -1) * (delta.end.row - delta.start.row);
    var deltaColShift =
      (deltaIsInsert ? 1 : -1) * (delta.end.column - delta.start.column);
    var deltaStart = delta.start;
    var deltaEnd = deltaIsInsert ? deltaStart : delta.end; // Collapse insert range.
    if ($pointsInOrder(point, deltaStart, moveIfEqual)) {
      return {
        row: point.row,
        column: point.column,
      };
    }
    if ($pointsInOrder(deltaEnd, point, !moveIfEqual)) {
      return {
        row: point.row + deltaRowShift,
        column: point.column + (point.row == deltaEnd.row ? deltaColShift : 0),
      };
    }
    return {
      row: deltaStart.row,
      column: deltaStart.column,
    };
  }
  exports.Anchor = Anchor;
});

define("ace/document", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/apply_delta",
  "ace/lib/event_emitter",
  "ace/range",
  "ace/anchor",
], function (require, exports, module) {
  "use strict";
  var oop = require("./lib/oop");
  var applyDelta = require("./apply_delta").applyDelta;
  var EventEmitter = require("./lib/event_emitter").EventEmitter;
  var Range = require("./range").Range;
  var Anchor = require("./anchor").Anchor;
  var Document = /** @class */ (function () {
    function Document(textOrLines) {
      this.$lines = [""];
      if (textOrLines.length === 0) {
        this.$lines = [""];
      } else if (Array.isArray(textOrLines)) {
        this.insertMergedLines({ row: 0, column: 0 }, textOrLines);
      } else {
        this.insert({ row: 0, column: 0 }, textOrLines);
      }
    }
    Document.prototype.setValue = function (text) {
      var len = this.getLength() - 1;
      this.remove(new Range(0, 0, len, this.getLine(len).length));
      this.insert({ row: 0, column: 0 }, text || "");
    };
    Document.prototype.getValue = function () {
      return this.getAllLines().join(this.getNewLineCharacter());
    };
    Document.prototype.createAnchor = function (row, column) {
      return new Anchor(this, row, column);
    };
    Document.prototype.$detectNewLine = function (text) {
      var match = text.match(/^.*?(\r\n|\r|\n)/m);
      this.$autoNewLine = match ? match[1] : "\n";
      this._signal("changeNewLineMode");
    };
    Document.prototype.getNewLineCharacter = function () {
      switch (this.$newLineMode) {
        case "windows":
          return "\r\n";
        case "unix":
          return "\n";
        default:
          return this.$autoNewLine || "\n";
      }
    };
    Document.prototype.setNewLineMode = function (newLineMode) {
      if (this.$newLineMode === newLineMode) return;
      this.$newLineMode = newLineMode;
      this._signal("changeNewLineMode");
    };
    Document.prototype.getNewLineMode = function () {
      return this.$newLineMode;
    };
    Document.prototype.isNewLine = function (text) {
      return text == "\r\n" || text == "\r" || text == "\n";
    };
    Document.prototype.getLine = function (row) {
      return this.$lines[row] || "";
    };
    Document.prototype.getLines = function (firstRow, lastRow) {
      return this.$lines.slice(firstRow, lastRow + 1);
    };
    Document.prototype.getAllLines = function () {
      return this.getLines(0, this.getLength());
    };
    Document.prototype.getLength = function () {
      return this.$lines.length;
    };
    Document.prototype.getTextRange = function (range) {
      return this.getLinesForRange(range).join(this.getNewLineCharacter());
    };
    Document.prototype.getLinesForRange = function (range) {
      var lines;
      if (range.start.row === range.end.row) {
        lines = [
          this.getLine(range.start.row).substring(
            range.start.column,
            range.end.column,
          ),
        ];
      } else {
        lines = this.getLines(range.start.row, range.end.row);
        lines[0] = (lines[0] || "").substring(range.start.column);
        var l = lines.length - 1;
        if (range.end.row - range.start.row == l)
          lines[l] = lines[l].substring(0, range.end.column);
      }
      return lines;
    };
    Document.prototype.insertLines = function (row, lines) {
      console.warn(
        "Use of document.insertLines is deprecated. Use the insertFullLines method instead.",
      );
      return this.insertFullLines(row, lines);
    };
    Document.prototype.removeLines = function (firstRow, lastRow) {
      console.warn(
        "Use of document.removeLines is deprecated. Use the removeFullLines method instead.",
      );
      return this.removeFullLines(firstRow, lastRow);
    };
    Document.prototype.insertNewLine = function (position) {
      console.warn(
        "Use of document.insertNewLine is deprecated. Use insertMergedLines(position, ['', '']) instead.",
      );
      return this.insertMergedLines(position, ["", ""]);
    };
    Document.prototype.insert = function (position, text) {
      if (this.getLength() <= 1) this.$detectNewLine(text);
      return this.insertMergedLines(position, this.$split(text));
    };
    Document.prototype.insertInLine = function (position, text) {
      var start = this.clippedPos(position.row, position.column);
      var end = this.pos(position.row, position.column + text.length);
      this.applyDelta(
        {
          start: start,
          end: end,
          action: "insert",
          lines: [text],
        },
        true,
      );
      return this.clonePos(end);
    };
    Document.prototype.clippedPos = function (row, column) {
      var length = this.getLength();
      if (row === undefined) {
        row = length;
      } else if (row < 0) {
        row = 0;
      } else if (row >= length) {
        row = length - 1;
        column = undefined;
      }
      var line = this.getLine(row);
      if (column == undefined) column = line.length;
      column = Math.min(Math.max(column, 0), line.length);
      return { row: row, column: column };
    };
    Document.prototype.clonePos = function (pos) {
      return { row: pos.row, column: pos.column };
    };
    Document.prototype.pos = function (row, column) {
      return { row: row, column: column };
    };
    Document.prototype.$clipPosition = function (position) {
      var length = this.getLength();
      if (position.row >= length) {
        position.row = Math.max(0, length - 1);
        position.column = this.getLine(length - 1).length;
      } else {
        position.row = Math.max(0, position.row);
        position.column = Math.min(
          Math.max(position.column, 0),
          this.getLine(position.row).length,
        );
      }
      return position;
    };
    Document.prototype.insertFullLines = function (row, lines) {
      row = Math.min(Math.max(row, 0), this.getLength());
      var column = 0;
      if (row < this.getLength()) {
        lines = lines.concat([""]);
        column = 0;
      } else {
        lines = [""].concat(lines);
        row--;
        column = this.$lines[row].length;
      }
      this.insertMergedLines({ row: row, column: column }, lines);
    };
    Document.prototype.insertMergedLines = function (position, lines) {
      var start = this.clippedPos(position.row, position.column);
      var end = {
        row: start.row + lines.length - 1,
        column:
          (lines.length == 1 ? start.column : 0) +
          lines[lines.length - 1].length,
      };
      this.applyDelta({
        start: start,
        end: end,
        action: "insert",
        lines: lines,
      });
      return this.clonePos(end);
    };
    Document.prototype.remove = function (range) {
      var start = this.clippedPos(range.start.row, range.start.column);
      var end = this.clippedPos(range.end.row, range.end.column);
      this.applyDelta({
        start: start,
        end: end,
        action: "remove",
        lines: this.getLinesForRange({ start: start, end: end }),
      });
      return this.clonePos(start);
    };
    Document.prototype.removeInLine = function (row, startColumn, endColumn) {
      var start = this.clippedPos(row, startColumn);
      var end = this.clippedPos(row, endColumn);
      this.applyDelta(
        {
          start: start,
          end: end,
          action: "remove",
          lines: this.getLinesForRange({ start: start, end: end }),
        },
        true,
      );
      return this.clonePos(start);
    };
    Document.prototype.removeFullLines = function (firstRow, lastRow) {
      firstRow = Math.min(Math.max(0, firstRow), this.getLength() - 1);
      lastRow = Math.min(Math.max(0, lastRow), this.getLength() - 1);
      var deleteFirstNewLine = lastRow == this.getLength() - 1 && firstRow > 0;
      var deleteLastNewLine = lastRow < this.getLength() - 1;
      var startRow = deleteFirstNewLine ? firstRow - 1 : firstRow;
      var startCol = deleteFirstNewLine ? this.getLine(startRow).length : 0;
      var endRow = deleteLastNewLine ? lastRow + 1 : lastRow;
      var endCol = deleteLastNewLine ? 0 : this.getLine(endRow).length;
      var range = new Range(startRow, startCol, endRow, endCol);
      var deletedLines = this.$lines.slice(firstRow, lastRow + 1);
      this.applyDelta({
        start: range.start,
        end: range.end,
        action: "remove",
        lines: this.getLinesForRange(range),
      });
      return deletedLines;
    };
    Document.prototype.removeNewLine = function (row) {
      if (row < this.getLength() - 1 && row >= 0) {
        this.applyDelta({
          start: this.pos(row, this.getLine(row).length),
          end: this.pos(row + 1, 0),
          action: "remove",
          lines: ["", ""],
        });
      }
    };
    Document.prototype.replace = function (range, text) {
      if (!(range instanceof Range))
        range = Range.fromPoints(range.start, range.end);
      if (text.length === 0 && range.isEmpty()) return range.start;
      if (text == this.getTextRange(range)) return range.end;
      this.remove(range);
      var end;
      if (text) {
        end = this.insert(range.start, text);
      } else {
        end = range.start;
      }
      return end;
    };
    Document.prototype.applyDeltas = function (deltas) {
      for (var i = 0; i < deltas.length; i++) {
        this.applyDelta(deltas[i]);
      }
    };
    Document.prototype.revertDeltas = function (deltas) {
      for (var i = deltas.length - 1; i >= 0; i--) {
        this.revertDelta(deltas[i]);
      }
    };
    Document.prototype.applyDelta = function (delta, doNotValidate) {
      var isInsert = delta.action == "insert";
      if (
        isInsert
          ? delta.lines.length <= 1 && !delta.lines[0]
          : !Range.comparePoints(delta.start, delta.end)
      ) {
        return;
      }
      if (isInsert && delta.lines.length > 20000) {
        this.$splitAndapplyLargeDelta(delta, 20000);
      } else {
        applyDelta(this.$lines, delta, doNotValidate);
        this._signal("change", delta);
      }
    };
    Document.prototype.$safeApplyDelta = function (delta) {
      var docLength = this.$lines.length;
      if (
        (delta.action == "remove" &&
          delta.start.row < docLength &&
          delta.end.row < docLength) ||
        (delta.action == "insert" && delta.start.row <= docLength)
      ) {
        this.applyDelta(delta);
      }
    };
    Document.prototype.$splitAndapplyLargeDelta = function (delta, MAX) {
      var lines = delta.lines;
      var l = lines.length - MAX + 1;
      var row = delta.start.row;
      var column = delta.start.column;
      for (var from = 0, to = 0; from < l; from = to) {
        to += MAX - 1;
        var chunk = lines.slice(from, to);
        chunk.push("");
        this.applyDelta(
          {
            start: this.pos(row + from, column),
            end: this.pos(row + to, (column = 0)),
            action: delta.action,
            lines: chunk,
          },
          true,
        );
      }
      delta.lines = lines.slice(from);
      delta.start.row = row + from;
      delta.start.column = column;
      this.applyDelta(delta, true);
    };
    Document.prototype.revertDelta = function (delta) {
      this.$safeApplyDelta({
        start: this.clonePos(delta.start),
        end: this.clonePos(delta.end),
        action: delta.action == "insert" ? "remove" : "insert",
        lines: delta.lines.slice(),
      });
    };
    Document.prototype.indexToPosition = function (index, startRow) {
      var lines = this.$lines || this.getAllLines();
      var newlineLength = this.getNewLineCharacter().length;
      for (var i = startRow || 0, l = lines.length; i < l; i++) {
        index -= lines[i].length + newlineLength;
        if (index < 0)
          return { row: i, column: index + lines[i].length + newlineLength };
      }
      return {
        row: l - 1,
        column: index + lines[l - 1].length + newlineLength,
      };
    };
    Document.prototype.positionToIndex = function (pos, startRow) {
      var lines = this.$lines || this.getAllLines();
      var newlineLength = this.getNewLineCharacter().length;
      var index = 0;
      var row = Math.min(pos.row, lines.length);
      for (var i = startRow || 0; i < row; ++i)
        index += lines[i].length + newlineLength;
      return index + pos.column;
    };
    Document.prototype.$split = function (text) {
      return text.split(/\r\n|\r|\n/);
    };
    return Document;
  })();
  Document.prototype.$autoNewLine = "";
  Document.prototype.$newLineMode = "auto";
  oop.implement(Document.prototype, EventEmitter);
  exports.Document = Document;
});

define("ace/background_tokenizer", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/event_emitter",
], function (require, exports, module) {
  "use strict";
  var oop = require("./lib/oop");
  var EventEmitter = require("./lib/event_emitter").EventEmitter;
  var BackgroundTokenizer = /** @class */ (function () {
    function BackgroundTokenizer(tokenizer, session) {
      this.running = false;
      this.lines = [];
      this.states = [];
      this.currentLine = 0;
      this.tokenizer = tokenizer;
      var self = this;
      this.$worker = function () {
        if (!self.running) {
          return;
        }
        var workerStart = new Date();
        var currentLine = self.currentLine;
        var endLine = -1;
        var doc = self.doc;
        var startLine = currentLine;
        while (self.lines[currentLine]) currentLine++;
        var len = doc.getLength();
        var processedLines = 0;
        self.running = false;
        while (currentLine < len) {
          self.$tokenizeRow(currentLine);
          endLine = currentLine;
          do {
            currentLine++;
          } while (self.lines[currentLine]);
          processedLines++;
          if (processedLines % 5 === 0 && new Date() - workerStart > 20) {
            self.running = setTimeout(self.$worker, 20);
            break;
          }
        }
        self.currentLine = currentLine;
        if (endLine == -1) endLine = currentLine;
        if (startLine <= endLine) self.fireUpdateEvent(startLine, endLine);
      };
    }
    BackgroundTokenizer.prototype.setTokenizer = function (tokenizer) {
      this.tokenizer = tokenizer;
      this.lines = [];
      this.states = [];
      this.start(0);
    };
    BackgroundTokenizer.prototype.setDocument = function (doc) {
      this.doc = doc;
      this.lines = [];
      this.states = [];
      this.stop();
    };
    BackgroundTokenizer.prototype.fireUpdateEvent = function (
      firstRow,
      lastRow,
    ) {
      var data = {
        first: firstRow,
        last: lastRow,
      };
      this._signal("update", { data: data });
    };
    BackgroundTokenizer.prototype.start = function (startRow) {
      this.currentLine = Math.min(
        startRow || 0,
        this.currentLine,
        this.doc.getLength(),
      );
      this.lines.splice(this.currentLine, this.lines.length);
      this.states.splice(this.currentLine, this.states.length);
      this.stop();
      this.running = setTimeout(this.$worker, 700);
    };
    BackgroundTokenizer.prototype.scheduleStart = function () {
      if (!this.running) this.running = setTimeout(this.$worker, 700);
    };
    BackgroundTokenizer.prototype.$updateOnChange = function (delta) {
      var startRow = delta.start.row;
      var len = delta.end.row - startRow;
      if (len === 0) {
        this.lines[startRow] = null;
      } else if (delta.action == "remove") {
        this.lines.splice(startRow, len + 1, null);
        this.states.splice(startRow, len + 1, null);
      } else {
        var args = Array(len + 1);
        args.unshift(startRow, 1);
        this.lines.splice.apply(this.lines, args);
        this.states.splice.apply(this.states, args);
      }
      this.currentLine = Math.min(
        startRow,
        this.currentLine,
        this.doc.getLength(),
      );
      this.stop();
    };
    BackgroundTokenizer.prototype.stop = function () {
      if (this.running) clearTimeout(this.running);
      this.running = false;
    };
    BackgroundTokenizer.prototype.getTokens = function (row) {
      return this.lines[row] || this.$tokenizeRow(row);
    };
    BackgroundTokenizer.prototype.getState = function (row) {
      if (this.currentLine == row) this.$tokenizeRow(row);
      return this.states[row] || "start";
    };
    BackgroundTokenizer.prototype.$tokenizeRow = function (row) {
      var line = this.doc.getLine(row);
      var state = this.states[row - 1];
      var data = this.tokenizer.getLineTokens(line, state, row);
      if (this.states[row] + "" !== data.state + "") {
        this.states[row] = data.state;
        this.lines[row + 1] = null;
        if (this.currentLine > row + 1) this.currentLine = row + 1;
      } else if (this.currentLine == row) {
        this.currentLine = row + 1;
      }
      return (this.lines[row] = data.tokens);
    };
    BackgroundTokenizer.prototype.cleanup = function () {
      this.running = false;
      this.lines = [];
      this.states = [];
      this.currentLine = 0;
      this.removeAllListeners();
    };
    return BackgroundTokenizer;
  })();
  oop.implement(BackgroundTokenizer.prototype, EventEmitter);
  exports.BackgroundTokenizer = BackgroundTokenizer;
});

define("ace/search_highlight", [
  "require",
  "exports",
  "module",
  "ace/lib/lang",
  "ace/range",
], function (require, exports, module) {
  "use strict";
  var lang = require("./lib/lang");
  var Range = require("./range").Range;
  var SearchHighlight = /** @class */ (function () {
    function SearchHighlight(regExp, clazz, type) {
      if (type === void 0) {
        type = "text";
      }
      this.setRegexp(regExp);
      this.clazz = clazz;
      this.type = type;
    }
    SearchHighlight.prototype.setRegexp = function (regExp) {
      if (this.regExp + "" == regExp + "") return;
      this.regExp = regExp;
      this.cache = [];
    };
    SearchHighlight.prototype.update = function (
      html,
      markerLayer,
      session,
      config,
    ) {
      if (!this.regExp) return;
      var start = config.firstRow,
        end = config.lastRow;
      var renderedMarkerRanges = {};
      for (var i = start; i <= end; i++) {
        var ranges = this.cache[i];
        if (ranges == null) {
          ranges = lang.getMatchOffsets(session.getLine(i), this.regExp);
          if (ranges.length > this.MAX_RANGES)
            ranges = ranges.slice(0, this.MAX_RANGES);
          ranges = ranges.map(function (match) {
            return new Range(i, match.offset, i, match.offset + match.length);
          });
          this.cache[i] = ranges.length ? ranges : "";
        }
        for (var j = ranges.length; j--; ) {
          var rangeToAddMarkerTo = ranges[j].toScreenRange(session);
          var rangeAsString = rangeToAddMarkerTo.toString();
          if (renderedMarkerRanges[rangeAsString]) continue;
          renderedMarkerRanges[rangeAsString] = true;
          markerLayer.drawSingleLineMarker(
            html,
            rangeToAddMarkerTo,
            this.clazz,
            config,
          );
        }
      }
    };
    return SearchHighlight;
  })();
  SearchHighlight.prototype.MAX_RANGES = 500;
  exports.SearchHighlight = SearchHighlight;
});

define("ace/undomanager", [
  "require",
  "exports",
  "module",
  "ace/range",
], function (require, exports, module) {
  "use strict";
  var UndoManager = /** @class */ (function () {
    function UndoManager() {
      this.$keepRedoStack;
      this.$maxRev = 0;
      this.$fromUndo = false;
      this.$undoDepth = Infinity;
      this.reset();
    }
    UndoManager.prototype.addSession = function (session) {
      this.$session = session;
    };
    UndoManager.prototype.add = function (delta, allowMerge, session) {
      if (this.$fromUndo) return;
      if (delta == this.$lastDelta) return;
      if (!this.$keepRedoStack) this.$redoStack.length = 0;
      if (allowMerge === false || !this.lastDeltas) {
        this.lastDeltas = [];
        var undoStackLength = this.$undoStack.length;
        if (undoStackLength > this.$undoDepth - 1) {
          this.$undoStack.splice(0, undoStackLength - this.$undoDepth + 1);
        }
        this.$undoStack.push(this.lastDeltas);
        delta.id = this.$rev = ++this.$maxRev;
      }
      if (delta.action == "remove" || delta.action == "insert")
        this.$lastDelta = delta;
      this.lastDeltas.push(delta);
    };
    UndoManager.prototype.addSelection = function (selection, rev) {
      this.selections.push({
        value: selection,
        rev: rev || this.$rev,
      });
    };
    UndoManager.prototype.startNewGroup = function () {
      this.lastDeltas = null;
      return this.$rev;
    };
    UndoManager.prototype.markIgnored = function (from, to) {
      if (to == null) to = this.$rev + 1;
      var stack = this.$undoStack;
      for (var i = stack.length; i--; ) {
        var delta = stack[i][0];
        if (delta.id <= from) break;
        if (delta.id < to) delta.ignore = true;
      }
      this.lastDeltas = null;
    };
    UndoManager.prototype.getSelection = function (rev, after) {
      var stack = this.selections;
      for (var i = stack.length; i--; ) {
        var selection = stack[i];
        if (selection.rev < rev) {
          if (after) selection = stack[i + 1];
          return selection;
        }
      }
    };
    UndoManager.prototype.getRevision = function () {
      return this.$rev;
    };
    UndoManager.prototype.getDeltas = function (from, to) {
      if (to == null) to = this.$rev + 1;
      var stack = this.$undoStack;
      var end = null,
        start = 0;
      for (var i = stack.length; i--; ) {
        var delta = stack[i][0];
        if (delta.id < to && !end) end = i + 1;
        if (delta.id <= from) {
          start = i + 1;
          break;
        }
      }
      return stack.slice(start, end);
    };
    UndoManager.prototype.getChangedRanges = function (from, to) {
      if (to == null) to = this.$rev + 1;
    };
    UndoManager.prototype.getChangedLines = function (from, to) {
      if (to == null) to = this.$rev + 1;
    };
    UndoManager.prototype.undo = function (session, dontSelect) {
      this.lastDeltas = null;
      var stack = this.$undoStack;
      if (!rearrangeUndoStack(stack, stack.length)) return;
      if (!session) session = this.$session;
      if (this.$redoStackBaseRev !== this.$rev && this.$redoStack.length)
        this.$redoStack = [];
      this.$fromUndo = true;
      var deltaSet = stack.pop();
      var undoSelectionRange = null;
      if (deltaSet) {
        undoSelectionRange = session.undoChanges(deltaSet, dontSelect);
        this.$redoStack.push(deltaSet);
        this.$syncRev();
      }
      this.$fromUndo = false;
      return undoSelectionRange;
    };
    UndoManager.prototype.redo = function (session, dontSelect) {
      this.lastDeltas = null;
      if (!session) session = this.$session;
      this.$fromUndo = true;
      if (this.$redoStackBaseRev != this.$rev) {
        var diff = this.getDeltas(this.$redoStackBaseRev, this.$rev + 1);
        rebaseRedoStack(this.$redoStack, diff);
        this.$redoStackBaseRev = this.$rev;
        this.$redoStack.forEach(function (x) {
          x[0].id = ++this.$maxRev;
        }, this);
      }
      var deltaSet = this.$redoStack.pop();
      var redoSelectionRange = null;
      if (deltaSet) {
        redoSelectionRange = session.redoChanges(deltaSet, dontSelect);
        this.$undoStack.push(deltaSet);
        this.$syncRev();
      }
      this.$fromUndo = false;
      return redoSelectionRange;
    };
    UndoManager.prototype.$syncRev = function () {
      var stack = this.$undoStack;
      var nextDelta = stack[stack.length - 1];
      var id = (nextDelta && nextDelta[0].id) || 0;
      this.$redoStackBaseRev = id;
      this.$rev = id;
    };
    UndoManager.prototype.reset = function () {
      this.lastDeltas = null;
      this.$lastDelta = null;
      this.$undoStack = [];
      this.$redoStack = [];
      this.$rev = 0;
      this.mark = 0;
      this.$redoStackBaseRev = this.$rev;
      this.selections = [];
    };
    UndoManager.prototype.canUndo = function () {
      return this.$undoStack.length > 0;
    };
    UndoManager.prototype.canRedo = function () {
      return this.$redoStack.length > 0;
    };
    UndoManager.prototype.bookmark = function (rev) {
      if (rev == undefined) rev = this.$rev;
      this.mark = rev;
    };
    UndoManager.prototype.isAtBookmark = function () {
      return this.$rev === this.mark;
    };
    UndoManager.prototype.toJSON = function () {
      return {
        $redoStack: this.$redoStack,
        $undoStack: this.$undoStack,
      };
    };
    UndoManager.prototype.fromJSON = function (json) {
      this.reset();
      this.$undoStack = json.$undoStack;
      this.$redoStack = json.$redoStack;
    };
    UndoManager.prototype.$prettyPrint = function (delta) {
      if (delta) return stringifyDelta(delta);
      return (
        stringifyDelta(this.$undoStack) +
        "\n---\n" +
        stringifyDelta(this.$redoStack)
      );
    };
    return UndoManager;
  })();
  UndoManager.prototype.hasUndo = UndoManager.prototype.canUndo;
  UndoManager.prototype.hasRedo = UndoManager.prototype.canRedo;
  UndoManager.prototype.isClean = UndoManager.prototype.isAtBookmark;
  UndoManager.prototype.markClean = UndoManager.prototype.bookmark;
  function rearrangeUndoStack(stack, pos) {
    for (var i = pos; i--; ) {
      var deltaSet = stack[i];
      if (deltaSet && !deltaSet[0].ignore) {
        while (i < pos - 1) {
          var swapped = swapGroups(stack[i], stack[i + 1]);
          stack[i] = swapped[0];
          stack[i + 1] = swapped[1];
          i++;
        }
        return true;
      }
    }
  }
  var Range = require("./range").Range;
  var cmp = Range.comparePoints;
  var comparePoints = Range.comparePoints;
  function $updateMarkers(delta) {
    var isInsert = delta.action == "insert";
    var start = delta.start;
    var end = delta.end;
    var rowShift = (end.row - start.row) * (isInsert ? 1 : -1);
    var colShift = (end.column - start.column) * (isInsert ? 1 : -1);
    if (isInsert) end = start;
    for (var i in this.marks) {
      var point = this.marks[i];
      var cmp = comparePoints(point, start);
      if (cmp < 0) {
        continue; // delta starts after the range
      }
      if (cmp === 0) {
        if (isInsert) {
          if (point.bias == 1) {
            cmp = 1;
          } else {
            point.bias == -1;
            continue;
          }
        }
      }
      var cmp2 = isInsert ? cmp : comparePoints(point, end);
      if (cmp2 > 0) {
        point.row += rowShift;
        point.column += point.row == end.row ? colShift : 0;
        continue;
      }
      if (!isInsert && cmp2 <= 0) {
        point.row = start.row;
        point.column = start.column;
        if (cmp2 === 0) point.bias = 1;
      }
    }
  }
  function clonePos(pos) {
    return { row: pos.row, column: pos.column };
  }
  function cloneDelta(d) {
    return {
      start: clonePos(d.start),
      end: clonePos(d.end),
      action: d.action,
      lines: d.lines.slice(),
    };
  }
  function stringifyDelta(d) {
    d = d || this;
    if (Array.isArray(d)) {
      return d.map(stringifyDelta).join("\n");
    }
    var type = "";
    if (d.action) {
      type = d.action == "insert" ? "+" : "-";
      type += "[" + d.lines + "]";
    } else if (d.value) {
      if (Array.isArray(d.value)) {
        type = d.value.map(stringifyRange).join("\n");
      } else {
        type = stringifyRange(d.value);
      }
    }
    if (d.start) {
      type += stringifyRange(d);
    }
    if (d.id || d.rev) {
      type += "\t(" + (d.id || d.rev) + ")";
    }
    return type;
  }
  function stringifyRange(r) {
    return (
      r.start.row + ":" + r.start.column + "=>" + r.end.row + ":" + r.end.column
    );
  }
  function swap(d1, d2) {
    var i1 = d1.action == "insert";
    var i2 = d2.action == "insert";
    if (i1 && i2) {
      if (cmp(d2.start, d1.end) >= 0) {
        shift(d2, d1, -1);
      } else if (cmp(d2.start, d1.start) <= 0) {
        shift(d1, d2, +1);
      } else {
        return null;
      }
    } else if (i1 && !i2) {
      if (cmp(d2.start, d1.end) >= 0) {
        shift(d2, d1, -1);
      } else if (cmp(d2.end, d1.start) <= 0) {
        shift(d1, d2, -1);
      } else {
        return null;
      }
    } else if (!i1 && i2) {
      if (cmp(d2.start, d1.start) >= 0) {
        shift(d2, d1, +1);
      } else if (cmp(d2.start, d1.start) <= 0) {
        shift(d1, d2, +1);
      } else {
        return null;
      }
    } else if (!i1 && !i2) {
      if (cmp(d2.start, d1.start) >= 0) {
        shift(d2, d1, +1);
      } else if (cmp(d2.end, d1.start) <= 0) {
        shift(d1, d2, -1);
      } else {
        return null;
      }
    }
    return [d2, d1];
  }
  function swapGroups(ds1, ds2) {
    for (var i = ds1.length; i--; ) {
      for (var j = 0; j < ds2.length; j++) {
        if (!swap(ds1[i], ds2[j])) {
          while (i < ds1.length) {
            while (j--) {
              swap(ds2[j], ds1[i]);
            }
            j = ds2.length;
            i++;
          }
          return [ds1, ds2];
        }
      }
    }
    ds1.selectionBefore =
      ds2.selectionBefore =
      ds1.selectionAfter =
      ds2.selectionAfter =
        null;
    return [ds2, ds1];
  }
  function xform(d1, c1) {
    var i1 = d1.action == "insert";
    var i2 = c1.action == "insert";
    if (i1 && i2) {
      if (cmp(d1.start, c1.start) < 0) {
        shift(c1, d1, 1);
      } else {
        shift(d1, c1, 1);
      }
    } else if (i1 && !i2) {
      if (cmp(d1.start, c1.end) >= 0) {
        shift(d1, c1, -1);
      } else if (cmp(d1.start, c1.start) <= 0) {
        shift(c1, d1, +1);
      } else {
        shift(d1, Range.fromPoints(c1.start, d1.start), -1);
        shift(c1, d1, +1);
      }
    } else if (!i1 && i2) {
      if (cmp(c1.start, d1.end) >= 0) {
        shift(c1, d1, -1);
      } else if (cmp(c1.start, d1.start) <= 0) {
        shift(d1, c1, +1);
      } else {
        shift(c1, Range.fromPoints(d1.start, c1.start), -1);
        shift(d1, c1, +1);
      }
    } else if (!i1 && !i2) {
      if (cmp(c1.start, d1.end) >= 0) {
        shift(c1, d1, -1);
      } else if (cmp(c1.end, d1.start) <= 0) {
        shift(d1, c1, -1);
      } else {
        var before, after;
        if (cmp(d1.start, c1.start) < 0) {
          before = d1;
          d1 = splitDelta(d1, c1.start);
        }
        if (cmp(d1.end, c1.end) > 0) {
          after = splitDelta(d1, c1.end);
        }
        shiftPos(c1.end, d1.start, d1.end, -1);
        if (after && !before) {
          d1.lines = after.lines;
          d1.start = after.start;
          d1.end = after.end;
          after = d1;
        }
        return [c1, before, after].filter(Boolean);
      }
    }
    return [c1, d1];
  }
  function shift(d1, d2, dir) {
    shiftPos(d1.start, d2.start, d2.end, dir);
    shiftPos(d1.end, d2.start, d2.end, dir);
  }
  function shiftPos(pos, start, end, dir) {
    if (pos.row == (dir == 1 ? start : end).row) {
      pos.column += dir * (end.column - start.column);
    }
    pos.row += dir * (end.row - start.row);
  }
  function splitDelta(c, pos) {
    var lines = c.lines;
    var end = c.end;
    c.end = clonePos(pos);
    var rowsBefore = c.end.row - c.start.row;
    var otherLines = lines.splice(rowsBefore, lines.length);
    var col = rowsBefore ? pos.column : pos.column - c.start.column;
    lines.push(otherLines[0].substring(0, col));
    otherLines[0] = otherLines[0].substr(col);
    var rest = {
      start: clonePos(pos),
      end: end,
      lines: otherLines,
      action: c.action,
    };
    return rest;
  }
  function moveDeltasByOne(redoStack, d) {
    d = cloneDelta(d);
    for (var j = redoStack.length; j--; ) {
      var deltaSet = redoStack[j];
      for (var i = 0; i < deltaSet.length; i++) {
        var x = deltaSet[i];
        var xformed = xform(x, d);
        d = xformed[0];
        if (xformed.length != 2) {
          if (xformed[2]) {
            deltaSet.splice(i + 1, 1, xformed[1], xformed[2]);
            i++;
          } else if (!xformed[1]) {
            deltaSet.splice(i, 1);
            i--;
          }
        }
      }
      if (!deltaSet.length) {
        redoStack.splice(j, 1);
      }
    }
    return redoStack;
  }
  function rebaseRedoStack(redoStack, deltaSets) {
    for (var i = 0; i < deltaSets.length; i++) {
      var deltas = deltaSets[i];
      for (var j = 0; j < deltas.length; j++) {
        moveDeltasByOne(redoStack, deltas[j]);
      }
    }
  }
  exports.UndoManager = UndoManager;
});

define("ace/edit_session/fold_line", [
  "require",
  "exports",
  "module",
  "ace/range",
], function (require, exports, module) {
  "use strict";
  var Range = require("../range").Range;
  var FoldLine = /** @class */ (function () {
    function FoldLine(foldData, folds) {
      this.foldData = foldData;
      if (Array.isArray(folds)) {
        this.folds = folds;
      } else {
        folds = this.folds = [folds];
      }
      var last = folds[folds.length - 1];
      this.range = new Range(
        folds[0].start.row,
        folds[0].start.column,
        last.end.row,
        last.end.column,
      );
      this.start = this.range.start;
      this.end = this.range.end;
      this.folds.forEach(function (fold) {
        fold.setFoldLine(this);
      }, this);
    }
    FoldLine.prototype.shiftRow = function (shift) {
      this.start.row += shift;
      this.end.row += shift;
      this.folds.forEach(function (fold) {
        fold.start.row += shift;
        fold.end.row += shift;
      });
    };
    FoldLine.prototype.addFold = function (fold) {
      if (fold.sameRow) {
        if (fold.start.row < this.startRow || fold.endRow > this.endRow) {
          throw new Error(
            "Can't add a fold to this FoldLine as it has no connection",
          );
        }
        this.folds.push(fold);
        this.folds.sort(function (a, b) {
          return -a.range.compareEnd(b.start.row, b.start.column);
        });
        if (this.range.compareEnd(fold.start.row, fold.start.column) > 0) {
          this.end.row = fold.end.row;
          this.end.column = fold.end.column;
        } else if (this.range.compareStart(fold.end.row, fold.end.column) < 0) {
          this.start.row = fold.start.row;
          this.start.column = fold.start.column;
        }
      } else if (fold.start.row == this.end.row) {
        this.folds.push(fold);
        this.end.row = fold.end.row;
        this.end.column = fold.end.column;
      } else if (fold.end.row == this.start.row) {
        this.folds.unshift(fold);
        this.start.row = fold.start.row;
        this.start.column = fold.start.column;
      } else {
        throw new Error(
          "Trying to add fold to FoldRow that doesn't have a matching row",
        );
      }
      fold.foldLine = this;
    };
    FoldLine.prototype.containsRow = function (row) {
      return row >= this.start.row && row <= this.end.row;
    };
    FoldLine.prototype.walk = function (callback, endRow, endColumn) {
      var lastEnd = 0,
        folds = this.folds,
        fold,
        cmp,
        stop,
        isNewRow = true;
      if (endRow == null) {
        endRow = this.end.row;
        endColumn = this.end.column;
      }
      for (var i = 0; i < folds.length; i++) {
        fold = folds[i];
        cmp = fold.range.compareStart(endRow, endColumn);
        if (cmp == -1) {
          callback(null, endRow, endColumn, lastEnd, isNewRow);
          return;
        }
        stop = callback(
          null,
          fold.start.row,
          fold.start.column,
          lastEnd,
          isNewRow,
        );
        stop =
          !stop &&
          callback(
            fold.placeholder,
            fold.start.row,
            fold.start.column,
            lastEnd,
          );
        if (stop || cmp === 0) {
          return;
        }
        isNewRow = !fold.sameRow;
        lastEnd = fold.end.column;
      }
      callback(null, endRow, endColumn, lastEnd, isNewRow);
    };
    FoldLine.prototype.getNextFoldTo = function (row, column) {
      var fold, cmp;
      for (var i = 0; i < this.folds.length; i++) {
        fold = this.folds[i];
        cmp = fold.range.compareEnd(row, column);
        if (cmp == -1) {
          return {
            fold: fold,
            kind: "after",
          };
        } else if (cmp === 0) {
          return {
            fold: fold,
            kind: "inside",
          };
        }
      }
      return null;
    };
    FoldLine.prototype.addRemoveChars = function (row, column, len) {
      var ret = this.getNextFoldTo(row, column),
        fold,
        folds;
      if (ret) {
        fold = ret.fold;
        if (
          ret.kind == "inside" &&
          fold.start.column != column &&
          fold.start.row != row
        ) {
          window.console && window.console.log(row, column, fold);
        } else if (fold.start.row == row) {
          folds = this.folds;
          var i = folds.indexOf(fold);
          if (i === 0) {
            this.start.column += len;
          }
          for (i; i < folds.length; i++) {
            fold = folds[i];
            fold.start.column += len;
            if (!fold.sameRow) {
              return;
            }
            fold.end.column += len;
          }
          this.end.column += len;
        }
      }
    };
    FoldLine.prototype.split = function (row, column) {
      var pos = this.getNextFoldTo(row, column);
      if (!pos || pos.kind == "inside") return null;
      var fold = pos.fold;
      var folds = this.folds;
      var foldData = this.foldData;
      var i = folds.indexOf(fold);
      var foldBefore = folds[i - 1];
      this.end.row = foldBefore.end.row;
      this.end.column = foldBefore.end.column;
      folds = folds.splice(i, folds.length - i);
      var newFoldLine = new FoldLine(foldData, folds);
      foldData.splice(foldData.indexOf(this) + 1, 0, newFoldLine);
      return newFoldLine;
    };
    FoldLine.prototype.merge = function (foldLineNext) {
      var folds = foldLineNext.folds;
      for (var i = 0; i < folds.length; i++) {
        this.addFold(folds[i]);
      }
      var foldData = this.foldData;
      foldData.splice(foldData.indexOf(foldLineNext), 1);
    };
    FoldLine.prototype.toString = function () {
      var ret = [this.range.toString() + ": ["];
      this.folds.forEach(function (fold) {
        ret.push("  " + fold.toString());
      });
      ret.push("]");
      return ret.join("\n");
    };
    FoldLine.prototype.idxToPosition = function (idx) {
      var lastFoldEndColumn = 0;
      for (var i = 0; i < this.folds.length; i++) {
        var fold = this.folds[i];
        idx -= fold.start.column - lastFoldEndColumn;
        if (idx < 0) {
          return {
            row: fold.start.row,
            column: fold.start.column + idx,
          };
        }
        idx -= fold.placeholder.length;
        if (idx < 0) {
          return fold.start;
        }
        lastFoldEndColumn = fold.end.column;
      }
      return {
        row: this.end.row,
        column: this.end.column + idx,
      };
    };
    return FoldLine;
  })();
  exports.FoldLine = FoldLine;
});

define("ace/range_list", [
  "require",
  "exports",
  "module",
  "ace/range",
], function (require, exports, module) {
  "use strict";
  var Range = require("./range").Range;
  var comparePoints = Range.comparePoints;
  var RangeList = /** @class */ (function () {
    function RangeList() {
      this.ranges = [];
      this.$bias = 1;
    }
    RangeList.prototype.pointIndex = function (pos, excludeEdges, startIndex) {
      var list = this.ranges;
      for (var i = startIndex || 0; i < list.length; i++) {
        var range = list[i];
        var cmpEnd = comparePoints(pos, range.end);
        if (cmpEnd > 0) continue;
        var cmpStart = comparePoints(pos, range.start);
        if (cmpEnd === 0) return excludeEdges && cmpStart !== 0 ? -i - 2 : i;
        if (cmpStart > 0 || (cmpStart === 0 && !excludeEdges)) return i;
        return -i - 1;
      }
      return -i - 1;
    };
    RangeList.prototype.add = function (range) {
      var excludeEdges = !range.isEmpty();
      var startIndex = this.pointIndex(range.start, excludeEdges);
      if (startIndex < 0) startIndex = -startIndex - 1;
      var endIndex = this.pointIndex(range.end, excludeEdges, startIndex);
      if (endIndex < 0) endIndex = -endIndex - 1;
      else endIndex++;
      return this.ranges.splice(startIndex, endIndex - startIndex, range);
    };
    RangeList.prototype.addList = function (list) {
      var removed = [];
      for (var i = list.length; i--; ) {
        removed.push.apply(removed, this.add(list[i]));
      }
      return removed;
    };
    RangeList.prototype.substractPoint = function (pos) {
      var i = this.pointIndex(pos);
      if (i >= 0) return this.ranges.splice(i, 1);
    };
    RangeList.prototype.merge = function () {
      var removed = [];
      var list = this.ranges;
      list = list.sort(function (a, b) {
        return comparePoints(a.start, b.start);
      });
      var next = list[0],
        range;
      for (var i = 1; i < list.length; i++) {
        range = next;
        next = list[i];
        var cmp = comparePoints(range.end, next.start);
        if (cmp < 0) continue;
        if (cmp == 0 && !range.isEmpty() && !next.isEmpty()) continue;
        if (comparePoints(range.end, next.end) < 0) {
          range.end.row = next.end.row;
          range.end.column = next.end.column;
        }
        list.splice(i, 1);
        removed.push(next);
        next = range;
        i--;
      }
      this.ranges = list;
      return removed;
    };
    RangeList.prototype.contains = function (row, column) {
      return this.pointIndex({ row: row, column: column }) >= 0;
    };
    RangeList.prototype.containsPoint = function (pos) {
      return this.pointIndex(pos) >= 0;
    };
    RangeList.prototype.rangeAtPoint = function (pos) {
      var i = this.pointIndex(pos);
      if (i >= 0) return this.ranges[i];
    };
    RangeList.prototype.clipRows = function (startRow, endRow) {
      var list = this.ranges;
      if (
        list[0].start.row > endRow ||
        list[list.length - 1].start.row < startRow
      )
        return [];
      var startIndex = this.pointIndex({ row: startRow, column: 0 });
      if (startIndex < 0) startIndex = -startIndex - 1;
      var endIndex = this.pointIndex({ row: endRow, column: 0 }, startIndex);
      if (endIndex < 0) endIndex = -endIndex - 1;
      var clipped = [];
      for (var i = startIndex; i < endIndex; i++) {
        clipped.push(list[i]);
      }
      return clipped;
    };
    RangeList.prototype.removeAll = function () {
      return this.ranges.splice(0, this.ranges.length);
    };
    RangeList.prototype.attach = function (session) {
      if (this.session) this.detach();
      this.session = session;
      this.onChange = this.$onChange.bind(this);
      this.session.on("change", this.onChange);
    };
    RangeList.prototype.detach = function () {
      if (!this.session) return;
      this.session.removeListener("change", this.onChange);
      this.session = null;
    };
    RangeList.prototype.$onChange = function (delta) {
      var start = delta.start;
      var end = delta.end;
      var startRow = start.row;
      var endRow = end.row;
      var ranges = this.ranges;
      for (var i = 0, n = ranges.length; i < n; i++) {
        var r = ranges[i];
        if (r.end.row >= startRow) break;
      }
      if (delta.action == "insert") {
        var lineDif = endRow - startRow;
        var colDiff = -start.column + end.column;
        for (; i < n; i++) {
          var r = ranges[i];
          if (r.start.row > startRow) break;
          if (r.start.row == startRow && r.start.column >= start.column) {
            if (r.start.column == start.column && this.$bias <= 0) {
            } else {
              r.start.column += colDiff;
              r.start.row += lineDif;
            }
          }
          if (r.end.row == startRow && r.end.column >= start.column) {
            if (r.end.column == start.column && this.$bias < 0) {
              continue;
            }
            if (r.end.column == start.column && colDiff > 0 && i < n - 1) {
              if (
                r.end.column > r.start.column &&
                r.end.column == ranges[i + 1].start.column
              )
                r.end.column -= colDiff;
            }
            r.end.column += colDiff;
            r.end.row += lineDif;
          }
        }
      } else {
        var lineDif = startRow - endRow;
        var colDiff = start.column - end.column;
        for (; i < n; i++) {
          var r = ranges[i];
          if (r.start.row > endRow) break;
          if (
            r.end.row < endRow &&
            (startRow < r.end.row ||
              (startRow == r.end.row && start.column < r.end.column))
          ) {
            r.end.row = startRow;
            r.end.column = start.column;
          } else if (r.end.row == endRow) {
            if (r.end.column <= end.column) {
              if (lineDif || r.end.column > start.column) {
                r.end.column = start.column;
                r.end.row = start.row;
              }
            } else {
              r.end.column += colDiff;
              r.end.row += lineDif;
            }
          } else if (r.end.row > endRow) {
            r.end.row += lineDif;
          }
          if (
            r.start.row < endRow &&
            (startRow < r.start.row ||
              (startRow == r.start.row && start.column < r.start.column))
          ) {
            r.start.row = startRow;
            r.start.column = start.column;
          } else if (r.start.row == endRow) {
            if (r.start.column <= end.column) {
              if (lineDif || r.start.column > start.column) {
                r.start.column = start.column;
                r.start.row = start.row;
              }
            } else {
              r.start.column += colDiff;
              r.start.row += lineDif;
            }
          } else if (r.start.row > endRow) {
            r.start.row += lineDif;
          }
        }
      }
      if (lineDif != 0 && i < n) {
        for (; i < n; i++) {
          var r = ranges[i];
          r.start.row += lineDif;
          r.end.row += lineDif;
        }
      }
    };
    return RangeList;
  })();
  RangeList.prototype.comparePoints = comparePoints;
  exports.RangeList = RangeList;
});

define("ace/edit_session/fold", [
  "require",
  "exports",
  "module",
  "ace/range_list",
], function (require, exports, module) {
  "use strict";
  var __extends =
    (this && this.__extends) ||
    (function () {
      var extendStatics = function (d, b) {
        extendStatics =
          Object.setPrototypeOf ||
          ({ __proto__: [] } instanceof Array &&
            function (d, b) {
              d.__proto__ = b;
            }) ||
          function (d, b) {
            for (var p in b)
              if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p];
          };
        return extendStatics(d, b);
      };
      return function (d, b) {
        if (typeof b !== "function" && b !== null)
          throw new TypeError(
            "Class extends value " +
              String(b) +
              " is not a constructor or null",
          );
        extendStatics(d, b);
        function __() {
          this.constructor = d;
        }
        d.prototype =
          b === null
            ? Object.create(b)
            : ((__.prototype = b.prototype), new __());
      };
    })();
  var RangeList = require("../range_list").RangeList;
  var Fold = /** @class */ (function (_super) {
    __extends(Fold, _super);
    function Fold(range, placeholder) {
      var _this = _super.call(this) || this;
      _this.foldLine = null;
      _this.placeholder = placeholder;
      _this.range = range;
      _this.start = range.start;
      _this.end = range.end;
      _this.sameRow = range.start.row == range.end.row;
      _this.subFolds = _this.ranges = [];
      return _this;
    }
    Fold.prototype.toString = function () {
      return '"' + this.placeholder + '" ' + this.range.toString();
    };
    Fold.prototype.setFoldLine = function (foldLine) {
      this.foldLine = foldLine;
      this.subFolds.forEach(function (fold) {
        fold.setFoldLine(foldLine);
      });
    };
    Fold.prototype.clone = function () {
      var range = this.range.clone();
      var fold = new Fold(range, this.placeholder);
      this.subFolds.forEach(function (subFold) {
        fold.subFolds.push(subFold.clone());
      });
      fold.collapseChildren = this.collapseChildren;
      return fold;
    };
    Fold.prototype.addSubFold = function (fold) {
      if (this.range.isEqual(fold)) return;
      consumeRange(fold, this.start);
      var row = fold.start.row,
        column = fold.start.column;
      for (var i = 0, cmp = -1; i < this.subFolds.length; i++) {
        cmp = this.subFolds[i].range.compare(row, column);
        if (cmp != 1) break;
      }
      var afterStart = this.subFolds[i];
      var firstConsumed = 0;
      if (cmp == 0) {
        if (afterStart.range.containsRange(fold))
          return afterStart.addSubFold(fold);
        else firstConsumed = 1;
      }
      var row = fold.range.end.row,
        column = fold.range.end.column;
      for (var j = i, cmp = -1; j < this.subFolds.length; j++) {
        cmp = this.subFolds[j].range.compare(row, column);
        if (cmp != 1) break;
      }
      if (cmp == 0) j++;
      var consumedFolds = this.subFolds.splice(i, j - i, fold);
      var last = cmp == 0 ? consumedFolds.length - 1 : consumedFolds.length;
      for (var k = firstConsumed; k < last; k++) {
        fold.addSubFold(consumedFolds[k]);
      }
      fold.setFoldLine(this.foldLine);
      return fold;
    };
    Fold.prototype.restoreRange = function (range) {
      return restoreRange(range, this.start);
    };
    return Fold;
  })(RangeList);
  function consumePoint(point, anchor) {
    point.row -= anchor.row;
    if (point.row == 0) point.column -= anchor.column;
  }
  function consumeRange(range, anchor) {
    consumePoint(range.start, anchor);
    consumePoint(range.end, anchor);
  }
  function restorePoint(point, anchor) {
    if (point.row == 0) point.column += anchor.column;
    point.row += anchor.row;
  }
  function restoreRange(range, anchor) {
    restorePoint(range.start, anchor);
    restorePoint(range.end, anchor);
  }
  exports.Fold = Fold;
});

define("ace/edit_session/folding", [
  "require",
  "exports",
  "module",
  "ace/range",
  "ace/edit_session/fold_line",
  "ace/edit_session/fold",
  "ace/token_iterator",
  "ace/mouse/mouse_event",
], function (require, exports, module) {
  // @ts-nocheck
  "use strict";
  var Range = require("../range").Range;
  var FoldLine = require("./fold_line").FoldLine;
  var Fold = require("./fold").Fold;
  var TokenIterator = require("../token_iterator").TokenIterator;
  var MouseEvent = require("../mouse/mouse_event").MouseEvent;
  function Folding() {
    this.getFoldAt = function (row, column, side) {
      var foldLine = this.getFoldLine(row);
      if (!foldLine) return null;
      var folds = foldLine.folds;
      for (var i = 0; i < folds.length; i++) {
        var range = folds[i].range;
        if (range.contains(row, column)) {
          if (side == 1 && range.isEnd(row, column) && !range.isEmpty()) {
            continue;
          } else if (
            side == -1 &&
            range.isStart(row, column) &&
            !range.isEmpty()
          ) {
            continue;
          }
          return folds[i];
        }
      }
    };
    this.getFoldsInRange = function (range) {
      var start = range.start;
      var end = range.end;
      var foldLines = this.$foldData;
      var foundFolds = [];
      start.column += 1;
      end.column -= 1;
      for (var i = 0; i < foldLines.length; i++) {
        var cmp = foldLines[i].range.compareRange(range);
        if (cmp == 2) {
          continue;
        } else if (cmp == -2) {
          break;
        }
        var folds = foldLines[i].folds;
        for (var j = 0; j < folds.length; j++) {
          var fold = folds[j];
          cmp = fold.range.compareRange(range);
          if (cmp == -2) {
            break;
          } else if (cmp == 2) {
            continue;
          } else if (cmp == 42) {
            break;
          }
          foundFolds.push(fold);
        }
      }
      start.column -= 1;
      end.column += 1;
      return foundFolds;
    };
    this.getFoldsInRangeList = function (ranges) {
      if (Array.isArray(ranges)) {
        var folds = [];
        ranges.forEach(function (range) {
          folds = folds.concat(this.getFoldsInRange(range));
        }, this);
      } else {
        var folds = this.getFoldsInRange(ranges);
      }
      return folds;
    };
    this.getAllFolds = function () {
      var folds = [];
      var foldLines = this.$foldData;
      for (var i = 0; i < foldLines.length; i++)
        for (var j = 0; j < foldLines[i].folds.length; j++)
          folds.push(foldLines[i].folds[j]);
      return folds;
    };
    this.getFoldStringAt = function (row, column, trim, foldLine) {
      foldLine = foldLine || this.getFoldLine(row);
      if (!foldLine) return null;
      var lastFold = {
        end: { column: 0 },
      };
      var str, fold;
      for (var i = 0; i < foldLine.folds.length; i++) {
        fold = foldLine.folds[i];
        var cmp = fold.range.compareEnd(row, column);
        if (cmp == -1) {
          str = this.getLine(fold.start.row).substring(
            lastFold.end.column,
            fold.start.column,
          );
          break;
        } else if (cmp === 0) {
          return null;
        }
        lastFold = fold;
      }
      if (!str)
        str = this.getLine(fold.start.row).substring(lastFold.end.column);
      if (trim == -1) return str.substring(0, column - lastFold.end.column);
      else if (trim == 1) return str.substring(column - lastFold.end.column);
      else return str;
    };
    this.getFoldLine = function (docRow, startFoldLine) {
      var foldData = this.$foldData;
      var i = 0;
      if (startFoldLine) i = foldData.indexOf(startFoldLine);
      if (i == -1) i = 0;
      for (i; i < foldData.length; i++) {
        var foldLine = foldData[i];
        if (foldLine.start.row <= docRow && foldLine.end.row >= docRow) {
          return foldLine;
        } else if (foldLine.end.row > docRow) {
          return null;
        }
      }
      return null;
    };
    this.getNextFoldLine = function (docRow, startFoldLine) {
      var foldData = this.$foldData;
      var i = 0;
      if (startFoldLine) i = foldData.indexOf(startFoldLine);
      if (i == -1) i = 0;
      for (i; i < foldData.length; i++) {
        var foldLine = foldData[i];
        if (foldLine.end.row >= docRow) {
          return foldLine;
        }
      }
      return null;
    };
    this.getFoldedRowCount = function (first, last) {
      var foldData = this.$foldData,
        rowCount = last - first + 1;
      for (var i = 0; i < foldData.length; i++) {
        var foldLine = foldData[i],
          end = foldLine.end.row,
          start = foldLine.start.row;
        if (end >= last) {
          if (start < last) {
            if (start >= first) rowCount -= last - start;
            else rowCount = 0; // in one fold
          }
          break;
        } else if (end >= first) {
          if (start >= first)
            // fold inside range
            rowCount -= end - start;
          else rowCount -= end - first + 1;
        }
      }
      return rowCount;
    };
    this.$addFoldLine = function (foldLine) {
      this.$foldData.push(foldLine);
      this.$foldData.sort(function (a, b) {
        return a.start.row - b.start.row;
      });
      return foldLine;
    };
    this.addFold = function (placeholder, range) {
      var foldData = this.$foldData;
      var added = false;
      var fold;
      if (placeholder instanceof Fold) fold = placeholder;
      else {
        fold = new Fold(range, placeholder);
        fold.collapseChildren = range.collapseChildren;
      }
      this.$clipRangeToDocument(fold.range);
      var startRow = fold.start.row;
      var startColumn = fold.start.column;
      var endRow = fold.end.row;
      var endColumn = fold.end.column;
      var startFold = this.getFoldAt(startRow, startColumn, 1);
      var endFold = this.getFoldAt(endRow, endColumn, -1);
      if (startFold && endFold == startFold) return startFold.addSubFold(fold);
      if (startFold && !startFold.range.isStart(startRow, startColumn))
        this.removeFold(startFold);
      if (endFold && !endFold.range.isEnd(endRow, endColumn))
        this.removeFold(endFold);
      var folds = this.getFoldsInRange(fold.range);
      if (folds.length > 0) {
        this.removeFolds(folds);
        if (!fold.collapseChildren) {
          folds.forEach(function (subFold) {
            fold.addSubFold(subFold);
          });
        }
      }
      for (var i = 0; i < foldData.length; i++) {
        var foldLine = foldData[i];
        if (endRow == foldLine.start.row) {
          foldLine.addFold(fold);
          added = true;
          break;
        } else if (startRow == foldLine.end.row) {
          foldLine.addFold(fold);
          added = true;
          if (!fold.sameRow) {
            var foldLineNext = foldData[i + 1];
            if (foldLineNext && foldLineNext.start.row == endRow) {
              foldLine.merge(foldLineNext);
              break;
            }
          }
          break;
        } else if (endRow <= foldLine.start.row) {
          break;
        }
      }
      if (!added)
        foldLine = this.$addFoldLine(new FoldLine(this.$foldData, fold));
      if (this.$useWrapMode)
        this.$updateWrapData(foldLine.start.row, foldLine.start.row);
      else this.$updateRowLengthCache(foldLine.start.row, foldLine.start.row);
      this.$modified = true;
      this._signal("changeFold", { data: fold, action: "add" });
      return fold;
    };
    this.addFolds = function (folds) {
      folds.forEach(function (fold) {
        this.addFold(fold);
      }, this);
    };
    this.removeFold = function (fold) {
      var foldLine = fold.foldLine;
      var startRow = foldLine.start.row;
      var endRow = foldLine.end.row;
      var foldLines = this.$foldData;
      var folds = foldLine.folds;
      if (folds.length == 1) {
        foldLines.splice(foldLines.indexOf(foldLine), 1);
      } else if (foldLine.range.isEnd(fold.end.row, fold.end.column)) {
        folds.pop();
        foldLine.end.row = folds[folds.length - 1].end.row;
        foldLine.end.column = folds[folds.length - 1].end.column;
      } else if (foldLine.range.isStart(fold.start.row, fold.start.column)) {
        folds.shift();
        foldLine.start.row = folds[0].start.row;
        foldLine.start.column = folds[0].start.column;
      } else if (fold.sameRow) {
        folds.splice(folds.indexOf(fold), 1);
      } else {
        var newFoldLine = foldLine.split(fold.start.row, fold.start.column);
        folds = newFoldLine.folds;
        folds.shift();
        newFoldLine.start.row = folds[0].start.row;
        newFoldLine.start.column = folds[0].start.column;
      }
      if (!this.$updating) {
        if (this.$useWrapMode) this.$updateWrapData(startRow, endRow);
        else this.$updateRowLengthCache(startRow, endRow);
      }
      this.$modified = true;
      this._signal("changeFold", { data: fold, action: "remove" });
    };
    this.removeFolds = function (folds) {
      var cloneFolds = [];
      for (var i = 0; i < folds.length; i++) {
        cloneFolds.push(folds[i]);
      }
      cloneFolds.forEach(function (fold) {
        this.removeFold(fold);
      }, this);
      this.$modified = true;
    };
    this.expandFold = function (fold) {
      this.removeFold(fold);
      fold.subFolds.forEach(function (subFold) {
        fold.restoreRange(subFold);
        this.addFold(subFold);
      }, this);
      if (fold.collapseChildren > 0) {
        this.foldAll(
          fold.start.row + 1,
          fold.end.row,
          fold.collapseChildren - 1,
        );
      }
      fold.subFolds = [];
    };
    this.expandFolds = function (folds) {
      folds.forEach(function (fold) {
        this.expandFold(fold);
      }, this);
    };
    this.unfold = function (location, expandInner) {
      var range, folds;
      if (location == null) {
        range = new Range(0, 0, this.getLength(), 0);
        if (expandInner == null) expandInner = true;
      } else if (typeof location == "number") {
        range = new Range(location, 0, location, this.getLine(location).length);
      } else if ("row" in location) {
        range = Range.fromPoints(location, location);
      } else if (Array.isArray(location)) {
        folds = [];
        location.forEach(function (range) {
          folds = folds.concat(this.unfold(range));
        }, this);
        return folds;
      } else {
        range = location;
      }
      folds = this.getFoldsInRangeList(range);
      var outermostFolds = folds;
      while (
        folds.length == 1 &&
        Range.comparePoints(folds[0].start, range.start) < 0 &&
        Range.comparePoints(folds[0].end, range.end) > 0
      ) {
        this.expandFolds(folds);
        folds = this.getFoldsInRangeList(range);
      }
      if (expandInner != false) {
        this.removeFolds(folds);
      } else {
        this.expandFolds(folds);
      }
      if (outermostFolds.length) return outermostFolds;
    };
    this.isRowFolded = function (docRow, startFoldRow) {
      return !!this.getFoldLine(docRow, startFoldRow);
    };
    this.getRowFoldEnd = function (docRow, startFoldRow) {
      var foldLine = this.getFoldLine(docRow, startFoldRow);
      return foldLine ? foldLine.end.row : docRow;
    };
    this.getRowFoldStart = function (docRow, startFoldRow) {
      var foldLine = this.getFoldLine(docRow, startFoldRow);
      return foldLine ? foldLine.start.row : docRow;
    };
    this.getFoldDisplayLine = function (
      foldLine,
      endRow,
      endColumn,
      startRow,
      startColumn,
    ) {
      if (startRow == null) startRow = foldLine.start.row;
      if (startColumn == null) startColumn = 0;
      if (endRow == null) endRow = foldLine.end.row;
      if (endColumn == null) endColumn = this.getLine(endRow).length;
      var doc = this.doc;
      var textLine = "";
      foldLine.walk(
        function (placeholder, row, column, lastColumn) {
          if (row < startRow) return;
          if (row == startRow) {
            if (column < startColumn) return;
            lastColumn = Math.max(startColumn, lastColumn);
          }
          if (placeholder != null) {
            textLine += placeholder;
          } else {
            textLine += doc.getLine(row).substring(lastColumn, column);
          }
        },
        endRow,
        endColumn,
      );
      return textLine;
    };
    this.getDisplayLine = function (row, endColumn, startRow, startColumn) {
      var foldLine = this.getFoldLine(row);
      if (!foldLine) {
        var line;
        line = this.doc.getLine(row);
        return line.substring(startColumn || 0, endColumn || line.length);
      } else {
        return this.getFoldDisplayLine(
          foldLine,
          row,
          endColumn,
          startRow,
          startColumn,
        );
      }
    };
    this.$cloneFoldData = function () {
      var fd = [];
      fd = this.$foldData.map(function (foldLine) {
        var folds = foldLine.folds.map(function (fold) {
          return fold.clone();
        });
        return new FoldLine(fd, folds);
      });
      return fd;
    };
    this.toggleFold = function (tryToUnfold) {
      var selection = this.selection;
      var range = selection.getRange();
      var fold;
      var bracketPos;
      if (range.isEmpty()) {
        var cursor = range.start;
        fold = this.getFoldAt(cursor.row, cursor.column);
        if (fold) {
          this.expandFold(fold);
          return;
        } else if ((bracketPos = this.findMatchingBracket(cursor))) {
          if (range.comparePoint(bracketPos) == 1) {
            range.end = bracketPos;
          } else {
            range.start = bracketPos;
            range.start.column++;
            range.end.column--;
          }
        } else if (
          (bracketPos = this.findMatchingBracket({
            row: cursor.row,
            column: cursor.column + 1,
          }))
        ) {
          if (range.comparePoint(bracketPos) == 1) range.end = bracketPos;
          else range.start = bracketPos;
          range.start.column++;
        } else {
          range = this.getCommentFoldRange(cursor.row, cursor.column) || range;
        }
      } else {
        var folds = this.getFoldsInRange(range);
        if (tryToUnfold && folds.length) {
          this.expandFolds(folds);
          return;
        } else if (folds.length == 1) {
          fold = folds[0];
        }
      }
      if (!fold) fold = this.getFoldAt(range.start.row, range.start.column);
      if (fold && fold.range.toString() == range.toString()) {
        this.expandFold(fold);
        return;
      }
      var placeholder = "...";
      if (!range.isMultiLine()) {
        placeholder = this.getTextRange(range);
        if (placeholder.length < 4) return;
        placeholder = placeholder.trim().substring(0, 2) + "..";
      }
      this.addFold(placeholder, range);
    };
    this.getCommentFoldRange = function (row, column, dir) {
      var iterator = new TokenIterator(this, row, column);
      var token = iterator.getCurrentToken();
      var type = token && token.type;
      if (token && /^comment|string/.test(type)) {
        type = type.match(/comment|string/)[0];
        if (type == "comment") type += "|doc-start|\\.doc";
        var re = new RegExp(type);
        var range = new Range();
        if (dir != 1) {
          do {
            token = iterator.stepBackward();
          } while (
            token &&
            re.test(token.type) &&
            !/^comment.end/.test(token.type)
          );
          token = iterator.stepForward();
        }
        range.start.row = iterator.getCurrentTokenRow();
        range.start.column =
          iterator.getCurrentTokenColumn() +
          (/^comment.start/.test(token.type) ? token.value.length : 2);
        iterator = new TokenIterator(this, row, column);
        if (dir != -1) {
          var lastRow = -1;
          do {
            token = iterator.stepForward();
            if (lastRow == -1) {
              var state = this.getState(iterator.$row);
              if (!re.test(state)) lastRow = iterator.$row;
            } else if (iterator.$row > lastRow) {
              break;
            }
          } while (
            token &&
            re.test(token.type) &&
            !/^comment.start/.test(token.type)
          );
          token = iterator.stepBackward();
        } else token = iterator.getCurrentToken();
        range.end.row = iterator.getCurrentTokenRow();
        range.end.column = iterator.getCurrentTokenColumn();
        if (!/^comment.end/.test(token.type)) {
          range.end.column += token.value.length - 2;
        }
        return range;
      }
    };
    this.foldAll = function (startRow, endRow, depth, test) {
      if (depth == undefined) depth = 100000; // JSON.stringify doesn't hanle Infinity
      var foldWidgets = this.foldWidgets;
      if (!foldWidgets) return; // mode doesn't support folding
      endRow = endRow || this.getLength();
      startRow = startRow || 0;
      for (var row = startRow; row < endRow; row++) {
        if (foldWidgets[row] == null)
          foldWidgets[row] = this.getFoldWidget(row);
        if (foldWidgets[row] != "start") continue;
        if (test && !test(row)) continue;
        var range = this.getFoldWidgetRange(row);
        if (
          range &&
          range.isMultiLine() &&
          range.end.row <= endRow &&
          range.start.row >= startRow
        ) {
          row = range.end.row;
          range.collapseChildren = depth;
          this.addFold("...", range);
        }
      }
    };
    this.foldToLevel = function (level) {
      this.foldAll();
      while (level-- > 0) this.unfold(null, false);
    };
    this.foldAllComments = function () {
      var session = this;
      this.foldAll(null, null, null, function (row) {
        var tokens = session.getTokens(row);
        for (var i = 0; i < tokens.length; i++) {
          var token = tokens[i];
          if (token.type == "text" && /^\s+$/.test(token.value)) continue;
          if (/comment/.test(token.type)) return true;
          return false;
        }
      });
    };
    this.$foldStyles = {
      manual: 1,
      markbegin: 1,
      markbeginend: 1,
    };
    this.$foldStyle = "markbegin";
    this.setFoldStyle = function (style) {
      if (!this.$foldStyles[style])
        throw new Error(
          "invalid fold style: " +
            style +
            "[" +
            Object.keys(this.$foldStyles).join(", ") +
            "]",
        );
      if (this.$foldStyle == style) return;
      this.$foldStyle = style;
      if (style == "manual") this.unfold();
      var mode = this.$foldMode;
      this.$setFolding(null);
      this.$setFolding(mode);
    };
    this.$setFolding = function (foldMode) {
      if (this.$foldMode == foldMode) return;
      this.$foldMode = foldMode;
      this.off("change", this.$updateFoldWidgets);
      this.off("tokenizerUpdate", this.$tokenizerUpdateFoldWidgets);
      this._signal("changeAnnotation");
      if (!foldMode || this.$foldStyle == "manual") {
        this.foldWidgets = null;
        return;
      }
      this.foldWidgets = [];
      this.getFoldWidget = foldMode.getFoldWidget.bind(
        foldMode,
        this,
        this.$foldStyle,
      );
      this.getFoldWidgetRange = foldMode.getFoldWidgetRange.bind(
        foldMode,
        this,
        this.$foldStyle,
      );
      this.$updateFoldWidgets = this.updateFoldWidgets.bind(this);
      this.$tokenizerUpdateFoldWidgets =
        this.tokenizerUpdateFoldWidgets.bind(this);
      this.on("change", this.$updateFoldWidgets);
      this.on("tokenizerUpdate", this.$tokenizerUpdateFoldWidgets);
    };
    this.getParentFoldRangeData = function (row, ignoreCurrent) {
      var fw = this.foldWidgets;
      if (!fw || (ignoreCurrent && fw[row])) return {};
      var i = row - 1,
        firstRange;
      while (i >= 0) {
        var c = fw[i];
        if (c == null) c = fw[i] = this.getFoldWidget(i);
        if (c == "start") {
          var range = this.getFoldWidgetRange(i);
          if (!firstRange) firstRange = range;
          if (range && range.end.row >= row) break;
        }
        i--;
      }
      return {
        range: i !== -1 && range,
        firstRange: firstRange,
      };
    };
    this.onFoldWidgetClick = function (row, e) {
      if (e instanceof MouseEvent) e = e.domEvent;
      var options = {
        children: e.shiftKey,
        all: e.ctrlKey || e.metaKey,
        siblings: e.altKey,
      };
      var range = this.$toggleFoldWidget(row, options);
      if (!range) {
        var el = e.target || e.srcElement;
        if (el && /ace_fold-widget/.test(el.className))
          el.className += " ace_invalid";
      }
    };
    this.$toggleFoldWidget = function (row, options) {
      if (!this.getFoldWidget) return;
      var type = this.getFoldWidget(row);
      var line = this.getLine(row);
      var dir = type === "end" ? -1 : 1;
      var fold = this.getFoldAt(row, dir === -1 ? 0 : line.length, dir);
      if (fold) {
        if (options.children || options.all) this.removeFold(fold);
        else this.expandFold(fold);
        return fold;
      }
      var range = this.getFoldWidgetRange(row, true);
      if (range && !range.isMultiLine()) {
        fold = this.getFoldAt(range.start.row, range.start.column, 1);
        if (fold && range.isEqual(fold.range)) {
          this.removeFold(fold);
          return fold;
        }
      }
      if (options.siblings) {
        var data = this.getParentFoldRangeData(row);
        if (data.range) {
          var startRow = data.range.start.row + 1;
          var endRow = data.range.end.row;
        }
        this.foldAll(startRow, endRow, options.all ? 10000 : 0);
      } else if (options.children) {
        endRow = range ? range.end.row : this.getLength();
        this.foldAll(row + 1, endRow, options.all ? 10000 : 0);
      } else if (range) {
        if (options.all) range.collapseChildren = 10000;
        this.addFold("...", range);
      }
      return range;
    };
    this.toggleFoldWidget = function (toggleParent) {
      var row = this.selection.getCursor().row;
      row = this.getRowFoldStart(row);
      var range = this.$toggleFoldWidget(row, {});
      if (range) return;
      var data = this.getParentFoldRangeData(row, true);
      range = data.range || data.firstRange;
      if (range) {
        row = range.start.row;
        var fold = this.getFoldAt(row, this.getLine(row).length, 1);
        if (fold) {
          this.removeFold(fold);
        } else {
          this.addFold("...", range);
        }
      }
    };
    this.updateFoldWidgets = function (delta) {
      var firstRow = delta.start.row;
      var len = delta.end.row - firstRow;
      if (len === 0) {
        this.foldWidgets[firstRow] = null;
      } else if (delta.action == "remove") {
        this.foldWidgets.splice(firstRow, len + 1, null);
      } else {
        var args = Array(len + 1);
        args.unshift(firstRow, 1);
        this.foldWidgets.splice.apply(this.foldWidgets, args);
      }
    };
    this.tokenizerUpdateFoldWidgets = function (e) {
      var rows = e.data;
      if (rows.first != rows.last) {
        if (this.foldWidgets.length > rows.first)
          this.foldWidgets.splice(rows.first, this.foldWidgets.length);
      }
    };
  }
  exports.Folding = Folding;
});

define("ace/edit_session/bracket_match", [
  "require",
  "exports",
  "module",
  "ace/token_iterator",
  "ace/range",
], function (require, exports, module) {
  "use strict";
  var TokenIterator = require("../token_iterator").TokenIterator;
  var Range = require("../range").Range;
  function BracketMatch() {
    this.findMatchingBracket = function (position, chr) {
      if (position.column == 0) return null;
      var charBeforeCursor =
        chr || this.getLine(position.row).charAt(position.column - 1);
      if (charBeforeCursor == "") return null;
      var match = charBeforeCursor.match(/([\(\[\{])|([\)\]\}])/);
      if (!match) return null;
      if (match[1]) return this.$findClosingBracket(match[1], position);
      else return this.$findOpeningBracket(match[2], position);
    };
    this.getBracketRange = function (pos) {
      var line = this.getLine(pos.row);
      var before = true,
        range;
      var chr = line.charAt(pos.column - 1);
      var match = chr && chr.match(/([\(\[\{])|([\)\]\}])/);
      if (!match) {
        chr = line.charAt(pos.column);
        pos = { row: pos.row, column: pos.column + 1 };
        match = chr && chr.match(/([\(\[\{])|([\)\]\}])/);
        before = false;
      }
      if (!match) return null;
      if (match[1]) {
        var bracketPos = this.$findClosingBracket(match[1], pos);
        if (!bracketPos) return null;
        range = Range.fromPoints(pos, bracketPos);
        if (!before) {
          range.end.column++;
          range.start.column--;
        }
        range.cursor = range.end;
      } else {
        var bracketPos = this.$findOpeningBracket(match[2], pos);
        if (!bracketPos) return null;
        range = Range.fromPoints(bracketPos, pos);
        if (!before) {
          range.start.column++;
          range.end.column--;
        }
        range.cursor = range.start;
      }
      return range;
    };
    this.getMatchingBracketRanges = function (pos, isBackwards) {
      var line = this.getLine(pos.row);
      var bracketsRegExp = /([\(\[\{])|([\)\]\}])/;
      var chr = !isBackwards && line.charAt(pos.column - 1);
      var match = chr && chr.match(bracketsRegExp);
      if (!match) {
        chr =
          (isBackwards === undefined || isBackwards) && line.charAt(pos.column);
        pos = {
          row: pos.row,
          column: pos.column + 1,
        };
        match = chr && chr.match(bracketsRegExp);
      }
      if (!match) return null;
      var startRange = new Range(pos.row, pos.column - 1, pos.row, pos.column);
      var bracketPos = match[1]
        ? this.$findClosingBracket(match[1], pos)
        : this.$findOpeningBracket(match[2], pos);
      if (!bracketPos) return [startRange];
      var endRange = new Range(
        bracketPos.row,
        bracketPos.column,
        bracketPos.row,
        bracketPos.column + 1,
      );
      return [startRange, endRange];
    };
    this.$brackets = {
      ")": "(",
      "(": ")",
      "]": "[",
      "[": "]",
      "{": "}",
      "}": "{",
      "<": ">",
      ">": "<",
    };
    this.$findOpeningBracket = function (bracket, position, typeRe) {
      var openBracket = this.$brackets[bracket];
      var depth = 1;
      var iterator = new TokenIterator(this, position.row, position.column);
      var token = iterator.getCurrentToken();
      if (!token) token = iterator.stepForward();
      if (!token) return;
      if (!typeRe) {
        typeRe = new RegExp(
          "(\\.?" +
            token.type
              .replace(".", "\\.")
              .replace("rparen", ".paren")
              .replace(/\b(?:end)\b/, "(?:start|begin|end)")
              .replace(/-close\b/, "-(close|open)") +
            ")+",
        );
      }
      var valueIndex = position.column - iterator.getCurrentTokenColumn() - 2;
      var value = token.value;
      while (true) {
        while (valueIndex >= 0) {
          var chr = value.charAt(valueIndex);
          if (chr == openBracket) {
            depth -= 1;
            if (depth == 0) {
              return {
                row: iterator.getCurrentTokenRow(),
                column: valueIndex + iterator.getCurrentTokenColumn(),
              };
            }
          } else if (chr == bracket) {
            depth += 1;
          }
          valueIndex -= 1;
        }
        do {
          token = iterator.stepBackward();
        } while (token && !typeRe.test(token.type));
        if (token == null) break;
        value = token.value;
        valueIndex = value.length - 1;
      }
      return null;
    };
    this.$findClosingBracket = function (bracket, position, typeRe) {
      var closingBracket = this.$brackets[bracket];
      var depth = 1;
      var iterator = new TokenIterator(this, position.row, position.column);
      var token = iterator.getCurrentToken();
      if (!token) token = iterator.stepForward();
      if (!token) return;
      if (!typeRe) {
        typeRe = new RegExp(
          "(\\.?" +
            token.type
              .replace(".", "\\.")
              .replace("lparen", ".paren")
              .replace(/\b(?:start|begin)\b/, "(?:start|begin|end)")
              .replace(/-open\b/, "-(close|open)") +
            ")+",
        );
      }
      var valueIndex = position.column - iterator.getCurrentTokenColumn();
      while (true) {
        var value = token.value;
        var valueLength = value.length;
        while (valueIndex < valueLength) {
          var chr = value.charAt(valueIndex);
          if (chr == closingBracket) {
            depth -= 1;
            if (depth == 0) {
              return {
                row: iterator.getCurrentTokenRow(),
                column: valueIndex + iterator.getCurrentTokenColumn(),
              };
            }
          } else if (chr == bracket) {
            depth += 1;
          }
          valueIndex += 1;
        }
        do {
          token = iterator.stepForward();
        } while (token && !typeRe.test(token.type));
        if (token == null) break;
        valueIndex = 0;
      }
      return null;
    };
    this.getMatchingTags = function (pos) {
      var iterator = new TokenIterator(this, pos.row, pos.column);
      var token = this.$findTagName(iterator);
      if (!token) return;
      var prevToken = iterator.stepBackward();
      if (prevToken.value === "<") {
        return this.$findClosingTag(iterator, token);
      } else {
        return this.$findOpeningTag(iterator, token);
      }
    };
    this.$findTagName = function (iterator) {
      var token = iterator.getCurrentToken();
      var found = false;
      var backward = false;
      if (token && token.type.indexOf("tag-name") === -1) {
        do {
          if (backward) token = iterator.stepBackward();
          else token = iterator.stepForward();
          if (token) {
            if (token.value === "/>") {
              backward = true;
            } else if (token.type.indexOf("tag-name") !== -1) {
              found = true;
            }
          }
        } while (token && !found);
      }
      return token;
    };
    this.$findClosingTag = function (iterator, token) {
      var prevToken;
      var currentTag = token.value;
      var tag = token.value;
      var depth = 0;
      var openTagStart = new Range(
        iterator.getCurrentTokenRow(),
        iterator.getCurrentTokenColumn(),
        iterator.getCurrentTokenRow(),
        iterator.getCurrentTokenColumn() + 1,
      );
      token = iterator.stepForward();
      var openTagName = new Range(
        iterator.getCurrentTokenRow(),
        iterator.getCurrentTokenColumn(),
        iterator.getCurrentTokenRow(),
        iterator.getCurrentTokenColumn() + token.value.length,
      );
      var foundOpenTagEnd = false;
      do {
        prevToken = token;
        token = iterator.stepForward();
        if (token) {
          if (token.value === ">" && !foundOpenTagEnd) {
            var openTagEnd = new Range(
              iterator.getCurrentTokenRow(),
              iterator.getCurrentTokenColumn(),
              iterator.getCurrentTokenRow(),
              iterator.getCurrentTokenColumn() + 1,
            ); //Range for `>`
            foundOpenTagEnd = true;
          }
          if (token.type.indexOf("tag-name") !== -1) {
            currentTag = token.value;
            if (tag === currentTag) {
              if (prevToken.value === "<") {
                depth++;
              } else if (prevToken.value === "</") {
                depth--;
                if (depth < 0) {
                  //found closing tag
                  iterator.stepBackward();
                  var closeTagStart = new Range(
                    iterator.getCurrentTokenRow(),
                    iterator.getCurrentTokenColumn(),
                    iterator.getCurrentTokenRow(),
                    iterator.getCurrentTokenColumn() + 2,
                  ); //Range for </
                  token = iterator.stepForward();
                  var closeTagName = new Range(
                    iterator.getCurrentTokenRow(),
                    iterator.getCurrentTokenColumn(),
                    iterator.getCurrentTokenRow(),
                    iterator.getCurrentTokenColumn() + token.value.length,
                  );
                  token = iterator.stepForward();
                  if (token && token.value === ">") {
                    var closeTagEnd = new Range(
                      iterator.getCurrentTokenRow(),
                      iterator.getCurrentTokenColumn(),
                      iterator.getCurrentTokenRow(),
                      iterator.getCurrentTokenColumn() + 1,
                    ); //Range for >
                  } else {
                    return;
                  }
                }
              }
            }
          } else if (tag === currentTag && token.value === "/>") {
            // self-closing tag
            depth--;
            if (depth < 0) {
              //found self-closing tag end
              var closeTagStart = new Range(
                iterator.getCurrentTokenRow(),
                iterator.getCurrentTokenColumn(),
                iterator.getCurrentTokenRow(),
                iterator.getCurrentTokenColumn() + 2,
              );
              var closeTagName = closeTagStart;
              var closeTagEnd = closeTagName;
              var openTagEnd = new Range(
                openTagName.end.row,
                openTagName.end.column,
                openTagName.end.row,
                openTagName.end.column + 1,
              );
            }
          }
        }
      } while (token && depth >= 0);
      if (
        openTagStart &&
        openTagEnd &&
        closeTagStart &&
        closeTagEnd &&
        openTagName &&
        closeTagName
      ) {
        return {
          openTag: new Range(
            openTagStart.start.row,
            openTagStart.start.column,
            openTagEnd.end.row,
            openTagEnd.end.column,
          ),
          closeTag: new Range(
            closeTagStart.start.row,
            closeTagStart.start.column,
            closeTagEnd.end.row,
            closeTagEnd.end.column,
          ),
          openTagName: openTagName,
          closeTagName: closeTagName,
        };
      }
    };
    this.$findOpeningTag = function (iterator, token) {
      var prevToken = iterator.getCurrentToken();
      var tag = token.value;
      var depth = 0;
      var startRow = iterator.getCurrentTokenRow();
      var startColumn = iterator.getCurrentTokenColumn();
      var endColumn = startColumn + 2;
      var closeTagStart = new Range(startRow, startColumn, startRow, endColumn); //Range for </
      iterator.stepForward();
      var closeTagName = new Range(
        iterator.getCurrentTokenRow(),
        iterator.getCurrentTokenColumn(),
        iterator.getCurrentTokenRow(),
        iterator.getCurrentTokenColumn() + token.value.length,
      );
      token = iterator.stepForward();
      if (!token || token.value !== ">") return;
      var closeTagEnd = new Range(
        iterator.getCurrentTokenRow(),
        iterator.getCurrentTokenColumn(),
        iterator.getCurrentTokenRow(),
        iterator.getCurrentTokenColumn() + 1,
      ); //Range for >
      iterator.stepBackward();
      iterator.stepBackward();
      do {
        token = prevToken;
        startRow = iterator.getCurrentTokenRow();
        startColumn = iterator.getCurrentTokenColumn();
        endColumn = startColumn + token.value.length;
        prevToken = iterator.stepBackward();
        if (token) {
          if (token.type.indexOf("tag-name") !== -1) {
            if (tag === token.value) {
              if (prevToken.value === "<") {
                depth++;
                if (depth > 0) {
                  //found opening tag
                  var openTagName = new Range(
                    startRow,
                    startColumn,
                    startRow,
                    endColumn,
                  );
                  var openTagStart = new Range(
                    iterator.getCurrentTokenRow(),
                    iterator.getCurrentTokenColumn(),
                    iterator.getCurrentTokenRow(),
                    iterator.getCurrentTokenColumn() + 1,
                  ); //Range for <
                  do {
                    token = iterator.stepForward();
                  } while (token && token.value !== ">");
                  var openTagEnd = new Range(
                    iterator.getCurrentTokenRow(),
                    iterator.getCurrentTokenColumn(),
                    iterator.getCurrentTokenRow(),
                    iterator.getCurrentTokenColumn() + 1,
                  ); //Range for >
                }
              } else if (prevToken.value === "</") {
                depth--;
              }
            }
          } else if (token.value === "/>") {
            // self-closing tag
            var stepCount = 0;
            var tmpToken = prevToken;
            while (tmpToken) {
              if (
                tmpToken.type.indexOf("tag-name") !== -1 &&
                tmpToken.value === tag
              ) {
                depth--;
                break;
              } else if (tmpToken.value === "<") {
                break;
              }
              tmpToken = iterator.stepBackward();
              stepCount++;
            }
            for (var i = 0; i < stepCount; i++) {
              iterator.stepForward();
            }
          }
        }
      } while (prevToken && depth <= 0);
      if (
        openTagStart &&
        openTagEnd &&
        closeTagStart &&
        closeTagEnd &&
        openTagName &&
        closeTagName
      ) {
        return {
          openTag: new Range(
            openTagStart.start.row,
            openTagStart.start.column,
            openTagEnd.end.row,
            openTagEnd.end.column,
          ),
          closeTag: new Range(
            closeTagStart.start.row,
            closeTagStart.start.column,
            closeTagEnd.end.row,
            closeTagEnd.end.column,
          ),
          openTagName: openTagName,
          closeTagName: closeTagName,
        };
      }
    };
  }
  exports.BracketMatch = BracketMatch;
});

define("ace/edit_session", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/lang",
  "ace/bidihandler",
  "ace/config",
  "ace/lib/event_emitter",
  "ace/selection",
  "ace/mode/text",
  "ace/range",
  "ace/document",
  "ace/background_tokenizer",
  "ace/search_highlight",
  "ace/undomanager",
  "ace/edit_session/folding",
  "ace/edit_session/bracket_match",
], function (require, exports, module) {
  "use strict";
  var oop = require("./lib/oop");
  var lang = require("./lib/lang");
  var BidiHandler = require("./bidihandler").BidiHandler;
  var config = require("./config");
  var EventEmitter = require("./lib/event_emitter").EventEmitter;
  var Selection = require("./selection").Selection;
  var TextMode = require("./mode/text").Mode;
  var Range = require("./range").Range;
  var Document = require("./document").Document;
  var BackgroundTokenizer =
    require("./background_tokenizer").BackgroundTokenizer;
  var SearchHighlight = require("./search_highlight").SearchHighlight;
  var UndoManager = require("./undomanager").UndoManager;
  var EditSession = /** @class */ (function () {
    function EditSession(text, mode) {
      this.doc;
      this.$breakpoints = [];
      this.$decorations = [];
      this.$frontMarkers = {};
      this.$backMarkers = {};
      this.$markerId = 1;
      this.$undoSelect = true;
      this.$foldData = [];
      this.id = "session" + ++EditSession.$uid;
      this.$foldData.toString = function () {
        return this.join("\n");
      };
      this.bgTokenizer = new BackgroundTokenizer(
        new TextMode().getTokenizer(),
        this,
      );
      var _self = this;
      this.bgTokenizer.on("update", function (e) {
        _self._signal("tokenizerUpdate", e);
      });
      this.on("changeFold", this.onChangeFold.bind(this));
      this.$onChange = this.onChange.bind(this);
      if (typeof text != "object" || !text.getLine)
        text = new Document(/**@type{string}*/ (text));
      this.setDocument(text);
      this.selection = new Selection(this);
      this.$bidiHandler = new BidiHandler(this);
      config.resetOptions(this);
      this.setMode(mode);
      config._signal("session", this);
      this.destroyed = false;
    }
    EditSession.prototype.setDocument = function (doc) {
      if (this.doc) this.doc.off("change", this.$onChange);
      this.doc = doc;
      doc.on("change", this.$onChange, true);
      this.bgTokenizer.setDocument(this.getDocument());
      this.resetCaches();
    };
    EditSession.prototype.getDocument = function () {
      return this.doc;
    };
    EditSession.prototype.$resetRowCache = function (docRow) {
      if (!docRow) {
        this.$docRowCache = [];
        this.$screenRowCache = [];
        return;
      }
      var l = this.$docRowCache.length;
      var i = this.$getRowCacheIndex(this.$docRowCache, docRow) + 1;
      if (l > i) {
        this.$docRowCache.splice(i, l);
        this.$screenRowCache.splice(i, l);
      }
    };
    EditSession.prototype.$getRowCacheIndex = function (cacheArray, val) {
      var low = 0;
      var hi = cacheArray.length - 1;
      while (low <= hi) {
        var mid = (low + hi) >> 1;
        var c = cacheArray[mid];
        if (val > c) low = mid + 1;
        else if (val < c) hi = mid - 1;
        else return mid;
      }
      return low - 1;
    };
    EditSession.prototype.resetCaches = function () {
      this.$modified = true;
      this.$wrapData = [];
      this.$rowLengthCache = [];
      this.$resetRowCache(0);
      if (!this.destroyed) this.bgTokenizer.start(0);
    };
    EditSession.prototype.onChangeFold = function (e) {
      var fold = e.data;
      this.$resetRowCache(fold.start.row);
    };
    EditSession.prototype.onChange = function (delta) {
      this.$modified = true;
      this.$bidiHandler.onChange(delta);
      this.$resetRowCache(delta.start.row);
      var removedFolds = this.$updateInternalDataOnChange(delta);
      if (!this.$fromUndo && this.$undoManager) {
        if (removedFolds && removedFolds.length) {
          this.$undoManager.add(
            {
              action: "removeFolds",
              folds: removedFolds,
            },
            this.mergeUndoDeltas,
          );
          this.mergeUndoDeltas = true;
        }
        this.$undoManager.add(delta, this.mergeUndoDeltas);
        this.mergeUndoDeltas = true;
        this.$informUndoManager.schedule();
      }
      this.bgTokenizer.$updateOnChange(delta);
      this._signal("change", delta);
    };
    EditSession.prototype.setValue = function (text) {
      this.doc.setValue(text);
      this.selection.moveTo(0, 0);
      this.$resetRowCache(0);
      this.setUndoManager(this.$undoManager);
      this.getUndoManager().reset();
    };
    EditSession.fromJSON = function (session) {
      if (typeof session == "string") session = JSON.parse(session);
      var undoManager = new UndoManager();
      undoManager.$undoStack = session.history.undo;
      undoManager.$redoStack = session.history.redo;
      undoManager.mark = session.history.mark;
      undoManager.$rev = session.history.rev;
      var editSession = new EditSession(session.value);
      session.folds.forEach(function (fold) {
        editSession.addFold("...", Range.fromPoints(fold.start, fold.end));
      });
      editSession.setAnnotations(session.annotations);
      editSession.setBreakpoints(session.breakpoints);
      editSession.setMode(session.mode);
      editSession.setScrollLeft(session.scrollLeft);
      editSession.setScrollTop(session.scrollTop);
      editSession.setUndoManager(undoManager);
      editSession.selection.fromJSON(session.selection);
      return editSession;
    };
    EditSession.prototype.toJSON = function () {
      return {
        annotations: this.$annotations,
        breakpoints: this.$breakpoints,
        folds: this.getAllFolds().map(function (fold) {
          return fold.range;
        }),
        history: this.getUndoManager(),
        mode: this.$mode.$id,
        scrollLeft: this.$scrollLeft,
        scrollTop: this.$scrollTop,
        selection: this.selection.toJSON(),
        value: this.doc.getValue(),
      };
    };
    EditSession.prototype.toString = function () {
      return this.doc.getValue();
    };
    EditSession.prototype.getSelection = function () {
      return this.selection;
    };
    EditSession.prototype.getState = function (row) {
      return this.bgTokenizer.getState(row);
    };
    EditSession.prototype.getTokens = function (row) {
      return this.bgTokenizer.getTokens(row);
    };
    EditSession.prototype.getTokenAt = function (row, column) {
      var tokens = this.bgTokenizer.getTokens(row);
      var token,
        c = 0;
      if (column == null) {
        var i = tokens.length - 1;
        c = this.getLine(row).length;
      } else {
        for (var i = 0; i < tokens.length; i++) {
          c += tokens[i].value.length;
          if (c >= column) break;
        }
      }
      token = tokens[i];
      if (!token) return null;
      token.index = i;
      token.start = c - token.value.length;
      return token;
    };
    EditSession.prototype.setUndoManager = function (undoManager) {
      this.$undoManager = undoManager;
      if (this.$informUndoManager) this.$informUndoManager.cancel();
      if (undoManager) {
        var self = this;
        undoManager.addSession(this);
        this.$syncInformUndoManager = function () {
          self.$informUndoManager.cancel();
          self.mergeUndoDeltas = false;
        };
        this.$informUndoManager = lang.delayedCall(this.$syncInformUndoManager);
      } else {
        this.$syncInformUndoManager = function () {};
      }
    };
    EditSession.prototype.markUndoGroup = function () {
      if (this.$syncInformUndoManager) this.$syncInformUndoManager();
    };
    EditSession.prototype.getUndoManager = function () {
      return this.$undoManager || this.$defaultUndoManager;
    };
    EditSession.prototype.getTabString = function () {
      if (this.getUseSoftTabs()) {
        return lang.stringRepeat(" ", this.getTabSize());
      } else {
        return "\t";
      }
    };
    EditSession.prototype.setUseSoftTabs = function (val) {
      this.setOption("useSoftTabs", val);
    };
    EditSession.prototype.getUseSoftTabs = function () {
      return this.$useSoftTabs && !this.$mode.$indentWithTabs;
    };
    EditSession.prototype.setTabSize = function (tabSize) {
      this.setOption("tabSize", tabSize);
    };
    EditSession.prototype.getTabSize = function () {
      return this.$tabSize;
    };
    EditSession.prototype.isTabStop = function (position) {
      return this.$useSoftTabs && position.column % this.$tabSize === 0;
    };
    EditSession.prototype.setNavigateWithinSoftTabs = function (
      navigateWithinSoftTabs,
    ) {
      this.setOption("navigateWithinSoftTabs", navigateWithinSoftTabs);
    };
    EditSession.prototype.getNavigateWithinSoftTabs = function () {
      return this.$navigateWithinSoftTabs;
    };
    EditSession.prototype.setOverwrite = function (overwrite) {
      this.setOption("overwrite", overwrite);
    };
    EditSession.prototype.getOverwrite = function () {
      return this.$overwrite;
    };
    EditSession.prototype.toggleOverwrite = function () {
      this.setOverwrite(!this.$overwrite);
    };
    EditSession.prototype.addGutterDecoration = function (row, className) {
      if (!this.$decorations[row]) this.$decorations[row] = "";
      this.$decorations[row] += " " + className;
      this._signal("changeBreakpoint", {});
    };
    EditSession.prototype.removeGutterDecoration = function (row, className) {
      this.$decorations[row] = (this.$decorations[row] || "").replace(
        " " + className,
        "",
      );
      this._signal("changeBreakpoint", {});
    };
    EditSession.prototype.getBreakpoints = function () {
      return this.$breakpoints;
    };
    EditSession.prototype.setBreakpoints = function (rows) {
      this.$breakpoints = [];
      for (var i = 0; i < rows.length; i++) {
        this.$breakpoints[rows[i]] = "ace_breakpoint";
      }
      this._signal("changeBreakpoint", {});
    };
    EditSession.prototype.clearBreakpoints = function () {
      this.$breakpoints = [];
      this._signal("changeBreakpoint", {});
    };
    EditSession.prototype.setBreakpoint = function (row, className) {
      if (className === undefined) className = "ace_breakpoint";
      if (className) this.$breakpoints[row] = className;
      else delete this.$breakpoints[row];
      this._signal("changeBreakpoint", {});
    };
    EditSession.prototype.clearBreakpoint = function (row) {
      delete this.$breakpoints[row];
      this._signal("changeBreakpoint", {});
    };
    EditSession.prototype.addMarker = function (range, clazz, type, inFront) {
      var id = this.$markerId++;
      var marker = {
        range: range,
        type: type || "line",
        renderer: typeof type == "function" ? type : null,
        clazz: clazz,
        inFront: !!inFront,
        id: id,
      };
      if (inFront) {
        this.$frontMarkers[id] = marker;
        this._signal("changeFrontMarker");
      } else {
        this.$backMarkers[id] = marker;
        this._signal("changeBackMarker");
      }
      return id;
    };
    EditSession.prototype.addDynamicMarker = function (marker, inFront) {
      if (!marker.update) return;
      var id = this.$markerId++;
      marker.id = id;
      marker.inFront = !!inFront;
      if (inFront) {
        this.$frontMarkers[id] = marker;
        this._signal("changeFrontMarker");
      } else {
        this.$backMarkers[id] = marker;
        this._signal("changeBackMarker");
      }
      return marker;
    };
    EditSession.prototype.removeMarker = function (markerId) {
      var marker = this.$frontMarkers[markerId] || this.$backMarkers[markerId];
      if (!marker) return;
      var markers = marker.inFront ? this.$frontMarkers : this.$backMarkers;
      delete markers[markerId];
      this._signal(marker.inFront ? "changeFrontMarker" : "changeBackMarker");
    };
    EditSession.prototype.getMarkers = function (inFront) {
      return inFront ? this.$frontMarkers : this.$backMarkers;
    };
    EditSession.prototype.highlight = function (re) {
      if (!this.$searchHighlight) {
        var highlight = new SearchHighlight(null, "ace_selected-word", "text");
        this.$searchHighlight = this.addDynamicMarker(highlight);
      }
      this.$searchHighlight.setRegexp(re);
    };
    EditSession.prototype.highlightLines = function (
      startRow,
      endRow,
      clazz,
      inFront,
    ) {
      if (typeof endRow != "number") {
        clazz = endRow;
        endRow = startRow;
      }
      if (!clazz) clazz = "ace_step";
      var range = new Range(startRow, 0, endRow, Infinity);
      range.id = this.addMarker(range, clazz, "fullLine", inFront);
      return range;
    };
    EditSession.prototype.setAnnotations = function (annotations) {
      this.$annotations = annotations;
      this._signal("changeAnnotation", {});
    };
    EditSession.prototype.getAnnotations = function () {
      return this.$annotations || [];
    };
    EditSession.prototype.clearAnnotations = function () {
      this.setAnnotations([]);
    };
    EditSession.prototype.$detectNewLine = function (text) {
      var match = text.match(/^.*?(\r?\n)/m);
      if (match) {
        this.$autoNewLine = match[1];
      } else {
        this.$autoNewLine = "\n";
      }
    };
    EditSession.prototype.getWordRange = function (row, column) {
      var line = this.getLine(row);
      var inToken = false;
      if (column > 0) inToken = !!line.charAt(column - 1).match(this.tokenRe);
      if (!inToken) inToken = !!line.charAt(column).match(this.tokenRe);
      if (inToken) var re = this.tokenRe;
      else if (/^\s+$/.test(line.slice(column - 1, column + 1))) var re = /\s/;
      else var re = this.nonTokenRe;
      var start = column;
      if (start > 0) {
        do {
          start--;
        } while (start >= 0 && line.charAt(start).match(re));
        start++;
      }
      var end = column;
      while (end < line.length && line.charAt(end).match(re)) {
        end++;
      }
      return new Range(row, start, row, end);
    };
    EditSession.prototype.getAWordRange = function (row, column) {
      var wordRange = this.getWordRange(row, column);
      var line = this.getLine(wordRange.end.row);
      while (line.charAt(wordRange.end.column).match(/[ \t]/)) {
        wordRange.end.column += 1;
      }
      return wordRange;
    };
    EditSession.prototype.setNewLineMode = function (newLineMode) {
      this.doc.setNewLineMode(newLineMode);
    };
    EditSession.prototype.getNewLineMode = function () {
      return this.doc.getNewLineMode();
    };
    EditSession.prototype.setUseWorker = function (useWorker) {
      this.setOption("useWorker", useWorker);
    };
    EditSession.prototype.getUseWorker = function () {
      return this.$useWorker;
    };
    EditSession.prototype.onReloadTokenizer = function (e) {
      var rows = e.data;
      this.bgTokenizer.start(rows.first);
      this._signal("tokenizerUpdate", e);
    };
    EditSession.prototype.setMode = function (mode, cb) {
      if (mode && typeof mode === "object") {
        if (mode.getTokenizer) return this.$onChangeMode(mode);
        var options = mode;
        var path = options.path;
      } else {
        path = /**@type{string}*/ (mode) || "ace/mode/text";
      }
      if (!this.$modes["ace/mode/text"])
        this.$modes["ace/mode/text"] = new TextMode();
      if (this.$modes[path] && !options) {
        this.$onChangeMode(this.$modes[path]);
        cb && cb();
        return;
      }
      this.$modeId = path;
      config.loadModule(
        ["mode", path],
        function (m) {
          if (this.$modeId !== path) return cb && cb();
          if (this.$modes[path] && !options) {
            this.$onChangeMode(this.$modes[path]);
          } else if (m && m.Mode) {
            m = new m.Mode(options);
            if (!options) {
              this.$modes[path] = m;
              m.$id = path;
            }
            this.$onChangeMode(m);
          }
          cb && cb();
        }.bind(this),
      );
      if (!this.$mode) this.$onChangeMode(this.$modes["ace/mode/text"], true);
    };
    EditSession.prototype.$onChangeMode = function (mode, $isPlaceholder) {
      if (!$isPlaceholder) this.$modeId = mode.$id;
      if (this.$mode === mode) return;
      var oldMode = this.$mode;
      this.$mode = mode;
      this.$stopWorker();
      if (this.$useWorker) this.$startWorker();
      var tokenizer = mode.getTokenizer();
      if (tokenizer.on !== undefined) {
        var onReloadTokenizer = this.onReloadTokenizer.bind(this);
        tokenizer.on("update", onReloadTokenizer);
      }
      this.bgTokenizer.setTokenizer(tokenizer);
      this.bgTokenizer.setDocument(this.getDocument());
      this.tokenRe = mode.tokenRe;
      this.nonTokenRe = mode.nonTokenRe;
      if (!$isPlaceholder) {
        if (mode.attachToSession) mode.attachToSession(this);
        this.$options.wrapMethod.set.call(this, this.$wrapMethod);
        this.$setFolding(mode.foldingRules);
        this.bgTokenizer.start(0);
        this._emit("changeMode", { oldMode: oldMode, mode: mode });
      }
    };
    EditSession.prototype.$stopWorker = function () {
      if (this.$worker) {
        this.$worker.terminate();
        this.$worker = null;
      }
    };
    EditSession.prototype.$startWorker = function () {
      try {
        this.$worker = this.$mode.createWorker(this);
      } catch (e) {
        config.warn("Could not load worker", e);
        this.$worker = null;
      }
    };
    EditSession.prototype.getMode = function () {
      return this.$mode;
    };
    EditSession.prototype.setScrollTop = function (scrollTop) {
      if (this.$scrollTop === scrollTop || isNaN(scrollTop)) return;
      this.$scrollTop = scrollTop;
      this._signal("changeScrollTop", scrollTop);
    };
    EditSession.prototype.getScrollTop = function () {
      return this.$scrollTop;
    };
    EditSession.prototype.setScrollLeft = function (scrollLeft) {
      if (this.$scrollLeft === scrollLeft || isNaN(scrollLeft)) return;
      this.$scrollLeft = scrollLeft;
      this._signal("changeScrollLeft", scrollLeft);
    };
    EditSession.prototype.getScrollLeft = function () {
      return this.$scrollLeft;
    };
    EditSession.prototype.getScreenWidth = function () {
      this.$computeWidth();
      if (this.lineWidgets)
        return Math.max(this.getLineWidgetMaxWidth(), this.screenWidth);
      return this.screenWidth;
    };
    EditSession.prototype.getLineWidgetMaxWidth = function () {
      if (this.lineWidgetsWidth != null) return this.lineWidgetsWidth;
      var width = 0;
      this.lineWidgets.forEach(function (w) {
        if (w && w.screenWidth > width) width = w.screenWidth;
      });
      return (this.lineWidgetWidth = width);
    };
    EditSession.prototype.$computeWidth = function (force) {
      if (this.$modified || force) {
        this.$modified = false;
        if (this.$useWrapMode) return (this.screenWidth = this.$wrapLimit);
        var lines = this.doc.getAllLines();
        var cache = this.$rowLengthCache;
        var longestScreenLine = 0;
        var foldIndex = 0;
        var foldLine = this.$foldData[foldIndex];
        var foldStart = foldLine ? foldLine.start.row : Infinity;
        var len = lines.length;
        for (var i = 0; i < len; i++) {
          if (i > foldStart) {
            i = foldLine.end.row + 1;
            if (i >= len) break;
            foldLine = this.$foldData[foldIndex++];
            foldStart = foldLine ? foldLine.start.row : Infinity;
          }
          if (cache[i] == null)
            cache[i] = this.$getStringScreenWidth(lines[i])[0];
          if (cache[i] > longestScreenLine) longestScreenLine = cache[i];
        }
        this.screenWidth = longestScreenLine;
      }
    };
    EditSession.prototype.getLine = function (row) {
      return this.doc.getLine(row);
    };
    EditSession.prototype.getLines = function (firstRow, lastRow) {
      return this.doc.getLines(firstRow, lastRow);
    };
    EditSession.prototype.getLength = function () {
      return this.doc.getLength();
    };
    EditSession.prototype.getTextRange = function (range) {
      return this.doc.getTextRange(range || this.selection.getRange());
    };
    EditSession.prototype.insert = function (position, text) {
      return this.doc.insert(position, text);
    };
    EditSession.prototype.remove = function (range) {
      return this.doc.remove(range);
    };
    EditSession.prototype.removeFullLines = function (firstRow, lastRow) {
      return this.doc.removeFullLines(firstRow, lastRow);
    };
    EditSession.prototype.undoChanges = function (deltas, dontSelect) {
      if (!deltas.length) return;
      this.$fromUndo = true;
      for (var i = deltas.length - 1; i != -1; i--) {
        var delta = deltas[i];
        if (delta.action == "insert" || delta.action == "remove") {
          this.doc.revertDelta(delta);
        } else if (delta.folds) {
          this.addFolds(delta.folds);
        }
      }
      if (!dontSelect && this.$undoSelect) {
        if (deltas.selectionBefore)
          this.selection.fromJSON(deltas.selectionBefore);
        else this.selection.setRange(this.$getUndoSelection(deltas, true));
      }
      this.$fromUndo = false;
    };
    EditSession.prototype.redoChanges = function (deltas, dontSelect) {
      if (!deltas.length) return;
      this.$fromUndo = true;
      for (var i = 0; i < deltas.length; i++) {
        var delta = deltas[i];
        if (delta.action == "insert" || delta.action == "remove") {
          this.doc.$safeApplyDelta(delta);
        }
      }
      if (!dontSelect && this.$undoSelect) {
        if (deltas.selectionAfter)
          this.selection.fromJSON(deltas.selectionAfter);
        else this.selection.setRange(this.$getUndoSelection(deltas, false));
      }
      this.$fromUndo = false;
    };
    EditSession.prototype.setUndoSelect = function (enable) {
      this.$undoSelect = enable;
    };
    EditSession.prototype.$getUndoSelection = function (deltas, isUndo) {
      function isInsert(delta) {
        return isUndo ? delta.action !== "insert" : delta.action === "insert";
      }
      var range, point;
      for (var i = 0; i < deltas.length; i++) {
        var delta = deltas[i];
        if (!delta.start) continue; // skip folds
        if (!range) {
          if (isInsert(delta)) {
            range = Range.fromPoints(delta.start, delta.end);
          } else {
            range = Range.fromPoints(delta.start, delta.start);
          }
          continue;
        }
        if (isInsert(delta)) {
          point = delta.start;
          if (range.compare(point.row, point.column) == -1) {
            range.setStart(point);
          }
          point = delta.end;
          if (range.compare(point.row, point.column) == 1) {
            range.setEnd(point);
          }
        } else {
          point = delta.start;
          if (range.compare(point.row, point.column) == -1) {
            range = Range.fromPoints(delta.start, delta.start);
          }
        }
      }
      return range;
    };
    EditSession.prototype.replace = function (range, text) {
      return this.doc.replace(range, text);
    };
    EditSession.prototype.moveText = function (fromRange, toPosition, copy) {
      var text = this.getTextRange(fromRange);
      var folds = this.getFoldsInRange(fromRange);
      var toRange = Range.fromPoints(toPosition, toPosition);
      if (!copy) {
        this.remove(fromRange);
        var rowDiff = fromRange.start.row - fromRange.end.row;
        var collDiff = rowDiff
          ? -fromRange.end.column
          : fromRange.start.column - fromRange.end.column;
        if (collDiff) {
          if (
            toRange.start.row == fromRange.end.row &&
            toRange.start.column > fromRange.end.column
          )
            toRange.start.column += collDiff;
          if (
            toRange.end.row == fromRange.end.row &&
            toRange.end.column > fromRange.end.column
          )
            toRange.end.column += collDiff;
        }
        if (rowDiff && toRange.start.row >= fromRange.end.row) {
          toRange.start.row += rowDiff;
          toRange.end.row += rowDiff;
        }
      }
      toRange.end = this.insert(toRange.start, text);
      if (folds.length) {
        var oldStart = fromRange.start;
        var newStart = toRange.start;
        var rowDiff = newStart.row - oldStart.row;
        var collDiff = newStart.column - oldStart.column;
        this.addFolds(
          folds.map(function (x) {
            x = x.clone();
            if (x.start.row == oldStart.row) x.start.column += collDiff;
            if (x.end.row == oldStart.row) x.end.column += collDiff;
            x.start.row += rowDiff;
            x.end.row += rowDiff;
            return x;
          }),
        );
      }
      return toRange;
    };
    EditSession.prototype.indentRows = function (
      startRow,
      endRow,
      indentString,
    ) {
      indentString = indentString.replace(/\t/g, this.getTabString());
      for (var row = startRow; row <= endRow; row++)
        this.doc.insertInLine({ row: row, column: 0 }, indentString);
    };
    EditSession.prototype.outdentRows = function (range) {
      var rowRange = range.collapseRows();
      var deleteRange = new Range(0, 0, 0, 0);
      var size = this.getTabSize();
      for (var i = rowRange.start.row; i <= rowRange.end.row; ++i) {
        var line = this.getLine(i);
        deleteRange.start.row = i;
        deleteRange.end.row = i;
        for (var j = 0; j < size; ++j) if (line.charAt(j) != " ") break;
        if (j < size && line.charAt(j) == "\t") {
          deleteRange.start.column = j;
          deleteRange.end.column = j + 1;
        } else {
          deleteRange.start.column = 0;
          deleteRange.end.column = j;
        }
        this.remove(deleteRange);
      }
    };
    EditSession.prototype.$moveLines = function (firstRow, lastRow, dir) {
      firstRow = this.getRowFoldStart(firstRow);
      lastRow = this.getRowFoldEnd(lastRow);
      if (dir < 0) {
        var row = this.getRowFoldStart(firstRow + dir);
        if (row < 0) return 0;
        var diff = row - firstRow;
      } else if (dir > 0) {
        var row = this.getRowFoldEnd(lastRow + dir);
        if (row > this.doc.getLength() - 1) return 0;
        var diff = row - lastRow;
      } else {
        firstRow = this.$clipRowToDocument(firstRow);
        lastRow = this.$clipRowToDocument(lastRow);
        var diff = lastRow - firstRow + 1;
      }
      var range = new Range(firstRow, 0, lastRow, Number.MAX_VALUE);
      var folds = this.getFoldsInRange(range).map(function (x) {
        x = x.clone();
        x.start.row += diff;
        x.end.row += diff;
        return x;
      });
      var lines =
        dir == 0
          ? this.doc.getLines(firstRow, lastRow)
          : this.doc.removeFullLines(firstRow, lastRow);
      this.doc.insertFullLines(firstRow + diff, lines);
      folds.length && this.addFolds(folds);
      return diff;
    };
    EditSession.prototype.moveLinesUp = function (firstRow, lastRow) {
      return this.$moveLines(firstRow, lastRow, -1);
    };
    EditSession.prototype.moveLinesDown = function (firstRow, lastRow) {
      return this.$moveLines(firstRow, lastRow, 1);
    };
    EditSession.prototype.duplicateLines = function (firstRow, lastRow) {
      return this.$moveLines(firstRow, lastRow, 0);
    };
    EditSession.prototype.$clipRowToDocument = function (row) {
      return Math.max(0, Math.min(row, this.doc.getLength() - 1));
    };
    EditSession.prototype.$clipColumnToRow = function (row, column) {
      if (column < 0) return 0;
      return Math.min(this.doc.getLine(row).length, column);
    };
    EditSession.prototype.$clipPositionToDocument = function (row, column) {
      column = Math.max(0, column);
      if (row < 0) {
        row = 0;
        column = 0;
      } else {
        var len = this.doc.getLength();
        if (row >= len) {
          row = len - 1;
          column = this.doc.getLine(len - 1).length;
        } else {
          column = Math.min(this.doc.getLine(row).length, column);
        }
      }
      return {
        row: row,
        column: column,
      };
    };
    EditSession.prototype.$clipRangeToDocument = function (range) {
      if (range.start.row < 0) {
        range.start.row = 0;
        range.start.column = 0;
      } else {
        range.start.column = this.$clipColumnToRow(
          range.start.row,
          range.start.column,
        );
      }
      var len = this.doc.getLength() - 1;
      if (range.end.row > len) {
        range.end.row = len;
        range.end.column = this.doc.getLine(len).length;
      } else {
        range.end.column = this.$clipColumnToRow(
          range.end.row,
          range.end.column,
        );
      }
      return range;
    };
    EditSession.prototype.setUseWrapMode = function (useWrapMode) {
      if (useWrapMode != this.$useWrapMode) {
        this.$useWrapMode = useWrapMode;
        this.$modified = true;
        this.$resetRowCache(0);
        if (useWrapMode) {
          var len = this.getLength();
          this.$wrapData = Array(len);
          this.$updateWrapData(0, len - 1);
        }
        this._signal("changeWrapMode");
      }
    };
    EditSession.prototype.getUseWrapMode = function () {
      return this.$useWrapMode;
    };
    EditSession.prototype.setWrapLimitRange = function (min, max) {
      if (
        this.$wrapLimitRange.min !== min ||
        this.$wrapLimitRange.max !== max
      ) {
        this.$wrapLimitRange = { min: min, max: max };
        this.$modified = true;
        this.$bidiHandler.markAsDirty();
        if (this.$useWrapMode) this._signal("changeWrapMode");
      }
    };
    EditSession.prototype.adjustWrapLimit = function (
      desiredLimit,
      $printMargin,
    ) {
      var limits = this.$wrapLimitRange;
      if (limits.max < 0) limits = { min: $printMargin, max: $printMargin };
      var wrapLimit = this.$constrainWrapLimit(
        desiredLimit,
        limits.min,
        limits.max,
      );
      if (wrapLimit != this.$wrapLimit && wrapLimit > 1) {
        this.$wrapLimit = wrapLimit;
        this.$modified = true;
        if (this.$useWrapMode) {
          this.$updateWrapData(0, this.getLength() - 1);
          this.$resetRowCache(0);
          this._signal("changeWrapLimit");
        }
        return true;
      }
      return false;
    };
    EditSession.prototype.$constrainWrapLimit = function (wrapLimit, min, max) {
      if (min) wrapLimit = Math.max(min, wrapLimit);
      if (max) wrapLimit = Math.min(max, wrapLimit);
      return wrapLimit;
    };
    EditSession.prototype.getWrapLimit = function () {
      return this.$wrapLimit;
    };
    EditSession.prototype.setWrapLimit = function (limit) {
      this.setWrapLimitRange(limit, limit);
    };
    EditSession.prototype.getWrapLimitRange = function () {
      return {
        min: this.$wrapLimitRange.min,
        max: this.$wrapLimitRange.max,
      };
    };
    EditSession.prototype.$updateInternalDataOnChange = function (delta) {
      var useWrapMode = this.$useWrapMode;
      var action = delta.action;
      var start = delta.start;
      var end = delta.end;
      var firstRow = start.row;
      var lastRow = end.row;
      var len = lastRow - firstRow;
      var removedFolds = null;
      this.$updating = true;
      if (len != 0) {
        if (action === "remove") {
          this[useWrapMode ? "$wrapData" : "$rowLengthCache"].splice(
            firstRow,
            len,
          );
          var foldLines = this.$foldData;
          removedFolds = this.getFoldsInRange(delta);
          this.removeFolds(removedFolds);
          var foldLine = this.getFoldLine(end.row);
          var idx = 0;
          if (foldLine) {
            foldLine.addRemoveChars(
              end.row,
              end.column,
              start.column - end.column,
            );
            foldLine.shiftRow(-len);
            var foldLineBefore = this.getFoldLine(firstRow);
            if (foldLineBefore && foldLineBefore !== foldLine) {
              foldLineBefore.merge(foldLine);
              foldLine = foldLineBefore;
            }
            idx = foldLines.indexOf(foldLine) + 1;
          }
          for (idx; idx < foldLines.length; idx++) {
            var foldLine = foldLines[idx];
            if (foldLine.start.row >= end.row) {
              foldLine.shiftRow(-len);
            }
          }
          lastRow = firstRow;
        } else {
          var args = Array(len);
          args.unshift(firstRow, 0);
          var arr = useWrapMode ? this.$wrapData : this.$rowLengthCache;
          arr.splice.apply(arr, args);
          var foldLines = this.$foldData;
          var foldLine = this.getFoldLine(firstRow);
          var idx = 0;
          if (foldLine) {
            var cmp = foldLine.range.compareInside(start.row, start.column);
            if (cmp == 0) {
              foldLine = foldLine.split(start.row, start.column);
              if (foldLine) {
                foldLine.shiftRow(len);
                foldLine.addRemoveChars(lastRow, 0, end.column - start.column);
              }
            } else if (cmp == -1) {
              foldLine.addRemoveChars(firstRow, 0, end.column - start.column);
              foldLine.shiftRow(len);
            }
            idx = foldLines.indexOf(foldLine) + 1;
          }
          for (idx; idx < foldLines.length; idx++) {
            var foldLine = foldLines[idx];
            if (foldLine.start.row >= firstRow) {
              foldLine.shiftRow(len);
            }
          }
        }
      } else {
        len = Math.abs(delta.start.column - delta.end.column);
        if (action === "remove") {
          removedFolds = this.getFoldsInRange(delta);
          this.removeFolds(removedFolds);
          len = -len;
        }
        var foldLine = this.getFoldLine(firstRow);
        if (foldLine) {
          foldLine.addRemoveChars(firstRow, start.column, len);
        }
      }
      if (useWrapMode && this.$wrapData.length != this.doc.getLength()) {
        console.error(
          "doc.getLength() and $wrapData.length have to be the same!",
        );
      }
      this.$updating = false;
      if (useWrapMode) this.$updateWrapData(firstRow, lastRow);
      else this.$updateRowLengthCache(firstRow, lastRow);
      return removedFolds;
    };
    EditSession.prototype.$updateRowLengthCache = function (firstRow, lastRow) {
      this.$rowLengthCache[firstRow] = null;
      this.$rowLengthCache[lastRow] = null;
    };
    EditSession.prototype.$updateWrapData = function (firstRow, lastRow) {
      var lines = this.doc.getAllLines();
      var tabSize = this.getTabSize();
      var wrapData = this.$wrapData;
      var wrapLimit = this.$wrapLimit;
      var tokens;
      var foldLine;
      var row = firstRow;
      lastRow = Math.min(lastRow, lines.length - 1);
      while (row <= lastRow) {
        foldLine = this.getFoldLine(row, foldLine);
        if (!foldLine) {
          tokens = this.$getDisplayTokens(lines[row]);
          wrapData[row] = this.$computeWrapSplits(tokens, wrapLimit, tabSize);
          row++;
        } else {
          tokens = [];
          foldLine.walk(
            function (placeholder, row, column, lastColumn) {
              var walkTokens;
              if (placeholder != null) {
                walkTokens = this.$getDisplayTokens(placeholder, tokens.length);
                walkTokens[0] = PLACEHOLDER_START;
                for (var i = 1; i < walkTokens.length; i++) {
                  walkTokens[i] = PLACEHOLDER_BODY;
                }
              } else {
                walkTokens = this.$getDisplayTokens(
                  lines[row].substring(lastColumn, column),
                  tokens.length,
                );
              }
              tokens = tokens.concat(walkTokens);
            }.bind(this),
            foldLine.end.row,
            lines[foldLine.end.row].length + 1,
          );
          wrapData[foldLine.start.row] = this.$computeWrapSplits(
            tokens,
            wrapLimit,
            tabSize,
          );
          row = foldLine.end.row + 1;
        }
      }
    };
    EditSession.prototype.$computeWrapSplits = function (
      tokens,
      wrapLimit,
      tabSize,
    ) {
      if (tokens.length == 0) {
        return [];
      }
      var splits = [];
      var displayLength = tokens.length;
      var lastSplit = 0,
        lastDocSplit = 0;
      var isCode = this.$wrapAsCode;
      var indentedSoftWrap = this.$indentedSoftWrap;
      var maxIndent =
        wrapLimit <= Math.max(2 * tabSize, 8) || indentedSoftWrap === false
          ? 0
          : Math.floor(wrapLimit / 2);
      function getWrapIndent() {
        var indentation = 0;
        if (maxIndent === 0) return indentation;
        if (indentedSoftWrap) {
          for (var i = 0; i < tokens.length; i++) {
            var token = tokens[i];
            if (token == SPACE) indentation += 1;
            else if (token == TAB) indentation += tabSize;
            else if (token == TAB_SPACE) continue;
            else break;
          }
        }
        if (isCode && indentedSoftWrap !== false) indentation += tabSize;
        return Math.min(indentation, maxIndent);
      }
      function addSplit(screenPos) {
        var len = screenPos - lastSplit;
        for (var i = lastSplit; i < screenPos; i++) {
          var ch = tokens[i];
          if (ch === 12 || ch === 2) len -= 1;
        }
        if (!splits.length) {
          indent = getWrapIndent();
          splits.indent = indent;
        }
        lastDocSplit += len;
        splits.push(lastDocSplit);
        lastSplit = screenPos;
      }
      var indent = 0;
      while (displayLength - lastSplit > wrapLimit - indent) {
        var split = lastSplit + wrapLimit - indent;
        if (tokens[split - 1] >= SPACE && tokens[split] >= SPACE) {
          addSplit(split);
          continue;
        }
        if (
          tokens[split] == PLACEHOLDER_START ||
          tokens[split] == PLACEHOLDER_BODY
        ) {
          for (split; split != lastSplit - 1; split--) {
            if (tokens[split] == PLACEHOLDER_START) {
              break;
            }
          }
          if (split > lastSplit) {
            addSplit(split);
            continue;
          }
          split = lastSplit + wrapLimit;
          for (split; split < tokens.length; split++) {
            if (tokens[split] != PLACEHOLDER_BODY) {
              break;
            }
          }
          if (split == tokens.length) {
            break; // Breaks the while-loop.
          }
          addSplit(split);
          continue;
        }
        var minSplit = Math.max(
          split - (wrapLimit - (wrapLimit >> 2)),
          lastSplit - 1,
        );
        while (split > minSplit && tokens[split] < PLACEHOLDER_START) {
          split--;
        }
        if (isCode) {
          while (split > minSplit && tokens[split] < PLACEHOLDER_START) {
            split--;
          }
          while (split > minSplit && tokens[split] == PUNCTUATION) {
            split--;
          }
        } else {
          while (split > minSplit && tokens[split] < SPACE) {
            split--;
          }
        }
        if (split > minSplit) {
          addSplit(++split);
          continue;
        }
        split = lastSplit + wrapLimit;
        if (tokens[split] == CHAR_EXT) split--;
        addSplit(split - indent);
      }
      return splits;
    };
    EditSession.prototype.$getDisplayTokens = function (str, offset) {
      var arr = [];
      var tabSize;
      offset = offset || 0;
      for (var i = 0; i < str.length; i++) {
        var c = str.charCodeAt(i);
        if (c == 9) {
          tabSize = this.getScreenTabSize(arr.length + offset);
          arr.push(TAB);
          for (var n = 1; n < tabSize; n++) {
            arr.push(TAB_SPACE);
          }
        } else if (c == 32) {
          arr.push(SPACE);
        } else if ((c > 39 && c < 48) || (c > 57 && c < 64)) {
          arr.push(PUNCTUATION);
        } else if (c >= 0x1100 && isFullWidth(c)) {
          arr.push(CHAR, CHAR_EXT);
        } else {
          arr.push(CHAR);
        }
      }
      return arr;
    };
    EditSession.prototype.$getStringScreenWidth = function (
      str,
      maxScreenColumn,
      screenColumn,
    ) {
      if (maxScreenColumn == 0) return [0, 0];
      if (maxScreenColumn == null) maxScreenColumn = Infinity;
      screenColumn = screenColumn || 0;
      var c, column;
      for (column = 0; column < str.length; column++) {
        c = str.charCodeAt(column);
        if (c == 9) {
          screenColumn += this.getScreenTabSize(screenColumn);
        } else if (c >= 0x1100 && isFullWidth(c)) {
          screenColumn += 2;
        } else {
          screenColumn += 1;
        }
        if (screenColumn > maxScreenColumn) {
          break;
        }
      }
      return [screenColumn, column];
    };
    EditSession.prototype.getRowLength = function (row) {
      var h = 1;
      if (this.lineWidgets)
        h += (this.lineWidgets[row] && this.lineWidgets[row].rowCount) || 0;
      if (!this.$useWrapMode || !this.$wrapData[row]) return h;
      else return this.$wrapData[row].length + h;
    };
    EditSession.prototype.getRowLineCount = function (row) {
      if (!this.$useWrapMode || !this.$wrapData[row]) {
        return 1;
      } else {
        return this.$wrapData[row].length + 1;
      }
    };
    EditSession.prototype.getRowWrapIndent = function (screenRow) {
      if (this.$useWrapMode) {
        var pos = this.screenToDocumentPosition(screenRow, Number.MAX_VALUE);
        var splits = this.$wrapData[pos.row];
        return splits.length && splits[0] < pos.column ? splits.indent : 0;
      } else {
        return 0;
      }
    };
    EditSession.prototype.getScreenLastRowColumn = function (screenRow) {
      var pos = this.screenToDocumentPosition(screenRow, Number.MAX_VALUE);
      return this.documentToScreenColumn(pos.row, pos.column);
    };
    EditSession.prototype.getDocumentLastRowColumn = function (
      docRow,
      docColumn,
    ) {
      var screenRow = this.documentToScreenRow(docRow, docColumn);
      return this.getScreenLastRowColumn(screenRow);
    };
    EditSession.prototype.getDocumentLastRowColumnPosition = function (
      docRow,
      docColumn,
    ) {
      var screenRow = this.documentToScreenRow(docRow, docColumn);
      return this.screenToDocumentPosition(screenRow, Number.MAX_VALUE / 10);
    };
    EditSession.prototype.getRowSplitData = function (row) {
      if (!this.$useWrapMode) {
        return undefined;
      } else {
        return this.$wrapData[row];
      }
    };
    EditSession.prototype.getScreenTabSize = function (screenColumn) {
      return this.$tabSize - (screenColumn % this.$tabSize | 0);
    };
    EditSession.prototype.screenToDocumentRow = function (
      screenRow,
      screenColumn,
    ) {
      return this.screenToDocumentPosition(screenRow, screenColumn).row;
    };
    EditSession.prototype.screenToDocumentColumn = function (
      screenRow,
      screenColumn,
    ) {
      return this.screenToDocumentPosition(screenRow, screenColumn).column;
    };
    EditSession.prototype.screenToDocumentPosition = function (
      screenRow,
      screenColumn,
      offsetX,
    ) {
      if (screenRow < 0) return { row: 0, column: 0 };
      var line;
      var docRow = 0;
      var docColumn = 0;
      var column;
      var row = 0;
      var rowLength = 0;
      var rowCache = this.$screenRowCache;
      var i = this.$getRowCacheIndex(rowCache, screenRow);
      var l = rowCache.length;
      if (l && i >= 0) {
        var row = rowCache[i];
        var docRow = this.$docRowCache[i];
        var doCache = screenRow > rowCache[l - 1];
      } else {
        var doCache = !l;
      }
      var maxRow = this.getLength() - 1;
      var foldLine = this.getNextFoldLine(docRow);
      var foldStart = foldLine ? foldLine.start.row : Infinity;
      while (row <= screenRow) {
        rowLength = this.getRowLength(docRow);
        if (row + rowLength > screenRow || docRow >= maxRow) {
          break;
        } else {
          row += rowLength;
          docRow++;
          if (docRow > foldStart) {
            docRow = foldLine.end.row + 1;
            foldLine = this.getNextFoldLine(docRow, foldLine);
            foldStart = foldLine ? foldLine.start.row : Infinity;
          }
        }
        if (doCache) {
          this.$docRowCache.push(docRow);
          this.$screenRowCache.push(row);
        }
      }
      if (foldLine && foldLine.start.row <= docRow) {
        line = this.getFoldDisplayLine(foldLine);
        docRow = foldLine.start.row;
      } else if (row + rowLength <= screenRow || docRow > maxRow) {
        return {
          row: maxRow,
          column: this.getLine(maxRow).length,
        };
      } else {
        line = this.getLine(docRow);
        foldLine = null;
      }
      var wrapIndent = 0,
        splitIndex = Math.floor(screenRow - row);
      if (this.$useWrapMode) {
        var splits = this.$wrapData[docRow];
        if (splits) {
          column = splits[splitIndex];
          if (splitIndex > 0 && splits.length) {
            wrapIndent = splits.indent;
            docColumn = splits[splitIndex - 1] || splits[splits.length - 1];
            line = line.substring(docColumn);
          }
        }
      }
      if (
        offsetX !== undefined &&
        this.$bidiHandler.isBidiRow(row + splitIndex, docRow, splitIndex)
      )
        screenColumn = this.$bidiHandler.offsetToCol(offsetX);
      docColumn += this.$getStringScreenWidth(
        line,
        screenColumn - wrapIndent,
      )[1];
      if (this.$useWrapMode && docColumn >= column) docColumn = column - 1;
      if (foldLine) return foldLine.idxToPosition(docColumn);
      return { row: docRow, column: docColumn };
    };
    EditSession.prototype.documentToScreenPosition = function (
      docRow,
      docColumn,
    ) {
      if (typeof docColumn === "undefined")
        var pos = this.$clipPositionToDocument(
          /**@type{Point}*/ (docRow).row,
          /**@type{Point}*/ (docRow).column,
        );
      else
        pos = this.$clipPositionToDocument(
          /**@type{number}*/ (docRow),
          docColumn,
        );
      docRow = pos.row;
      docColumn = pos.column;
      var screenRow = 0;
      var foldStartRow = null;
      var fold = null;
      fold = this.getFoldAt(docRow, docColumn, 1);
      if (fold) {
        docRow = fold.start.row;
        docColumn = fold.start.column;
      }
      var rowEnd,
        row = 0;
      var rowCache = this.$docRowCache;
      var i = this.$getRowCacheIndex(rowCache, docRow);
      var l = rowCache.length;
      if (l && i >= 0) {
        var row = rowCache[i];
        var screenRow = this.$screenRowCache[i];
        var doCache = docRow > rowCache[l - 1];
      } else {
        var doCache = !l;
      }
      var foldLine = this.getNextFoldLine(row);
      var foldStart = foldLine ? foldLine.start.row : Infinity;
      while (row < docRow) {
        if (row >= foldStart) {
          rowEnd = foldLine.end.row + 1;
          if (rowEnd > docRow) break;
          foldLine = this.getNextFoldLine(rowEnd, foldLine);
          foldStart = foldLine ? foldLine.start.row : Infinity;
        } else {
          rowEnd = row + 1;
        }
        screenRow += this.getRowLength(row);
        row = rowEnd;
        if (doCache) {
          this.$docRowCache.push(row);
          this.$screenRowCache.push(screenRow);
        }
      }
      var textLine = "";
      if (foldLine && row >= foldStart) {
        textLine = this.getFoldDisplayLine(foldLine, docRow, docColumn);
        foldStartRow = foldLine.start.row;
      } else {
        textLine = this.getLine(docRow).substring(0, docColumn);
        foldStartRow = docRow;
      }
      var wrapIndent = 0;
      if (this.$useWrapMode) {
        var wrapRow = this.$wrapData[foldStartRow];
        if (wrapRow) {
          var screenRowOffset = 0;
          while (textLine.length >= wrapRow[screenRowOffset]) {
            screenRow++;
            screenRowOffset++;
          }
          textLine = textLine.substring(
            wrapRow[screenRowOffset - 1] || 0,
            textLine.length,
          );
          wrapIndent = screenRowOffset > 0 ? wrapRow.indent : 0;
        }
      }
      if (
        this.lineWidgets &&
        this.lineWidgets[row] &&
        this.lineWidgets[row].rowsAbove
      )
        screenRow += this.lineWidgets[row].rowsAbove;
      return {
        row: screenRow,
        column: wrapIndent + this.$getStringScreenWidth(textLine)[0],
      };
    };
    EditSession.prototype.documentToScreenColumn = function (row, docColumn) {
      return this.documentToScreenPosition(row, docColumn).column;
    };
    EditSession.prototype.documentToScreenRow = function (docRow, docColumn) {
      return this.documentToScreenPosition(docRow, docColumn).row;
    };
    EditSession.prototype.getScreenLength = function () {
      var screenRows = 0;
      var fold = null;
      if (!this.$useWrapMode) {
        screenRows = this.getLength();
        var foldData = this.$foldData;
        for (var i = 0; i < foldData.length; i++) {
          fold = foldData[i];
          screenRows -= fold.end.row - fold.start.row;
        }
      } else {
        var lastRow = this.$wrapData.length;
        var row = 0,
          i = 0;
        var fold = this.$foldData[i++];
        var foldStart = fold ? fold.start.row : Infinity;
        while (row < lastRow) {
          var splits = this.$wrapData[row];
          screenRows += splits ? splits.length + 1 : 1;
          row++;
          if (row > foldStart) {
            row = fold.end.row + 1;
            fold = this.$foldData[i++];
            foldStart = fold ? fold.start.row : Infinity;
          }
        }
      }
      if (this.lineWidgets) screenRows += this.$getWidgetScreenLength();
      return screenRows;
    };
    EditSession.prototype.$setFontMetrics = function (fm) {
      if (!this.$enableVarChar) return;
      this.$getStringScreenWidth = function (
        str,
        maxScreenColumn,
        screenColumn,
      ) {
        if (maxScreenColumn === 0) return [0, 0];
        if (!maxScreenColumn) maxScreenColumn = Infinity;
        screenColumn = screenColumn || 0;
        var c, column;
        for (column = 0; column < str.length; column++) {
          c = str.charAt(column);
          if (c === "\t") {
            screenColumn += this.getScreenTabSize(screenColumn);
          } else {
            screenColumn += fm.getCharacterWidth(c);
          }
          if (screenColumn > maxScreenColumn) {
            break;
          }
        }
        return [screenColumn, column];
      };
    };
    EditSession.prototype.destroy = function () {
      if (!this.destroyed) {
        this.bgTokenizer.setDocument(null);
        this.bgTokenizer.cleanup();
        this.destroyed = true;
      }
      this.$stopWorker();
      this.removeAllListeners();
      if (this.doc) {
        this.doc.off("change", this.$onChange);
      }
      this.selection.detach();
    };
    return EditSession;
  })();
  EditSession.$uid = 0;
  EditSession.prototype.$modes = config.$modes;
  EditSession.prototype.getValue = EditSession.prototype.toString;
  EditSession.prototype.$defaultUndoManager = {
    undo: function () {},
    redo: function () {},
    hasUndo: function () {},
    hasRedo: function () {},
    reset: function () {},
    add: function () {},
    addSelection: function () {},
    startNewGroup: function () {},
    addSession: function () {},
  };
  EditSession.prototype.$overwrite = false;
  EditSession.prototype.$mode = null;
  EditSession.prototype.$modeId = null;
  EditSession.prototype.$scrollTop = 0;
  EditSession.prototype.$scrollLeft = 0;
  EditSession.prototype.$wrapLimit = 80;
  EditSession.prototype.$useWrapMode = false;
  EditSession.prototype.$wrapLimitRange = {
    min: null,
    max: null,
  };
  EditSession.prototype.lineWidgets = null;
  EditSession.prototype.isFullWidth = isFullWidth;
  oop.implement(EditSession.prototype, EventEmitter);
  var CHAR = 1,
    CHAR_EXT = 2,
    PLACEHOLDER_START = 3,
    PLACEHOLDER_BODY = 4,
    PUNCTUATION = 9,
    SPACE = 10,
    TAB = 11,
    TAB_SPACE = 12;
  function isFullWidth(c) {
    if (c < 0x1100) return false;
    return (
      (c >= 0x1100 && c <= 0x115f) ||
      (c >= 0x11a3 && c <= 0x11a7) ||
      (c >= 0x11fa && c <= 0x11ff) ||
      (c >= 0x2329 && c <= 0x232a) ||
      (c >= 0x2e80 && c <= 0x2e99) ||
      (c >= 0x2e9b && c <= 0x2ef3) ||
      (c >= 0x2f00 && c <= 0x2fd5) ||
      (c >= 0x2ff0 && c <= 0x2ffb) ||
      (c >= 0x3000 && c <= 0x303e) ||
      (c >= 0x3041 && c <= 0x3096) ||
      (c >= 0x3099 && c <= 0x30ff) ||
      (c >= 0x3105 && c <= 0x312d) ||
      (c >= 0x3131 && c <= 0x318e) ||
      (c >= 0x3190 && c <= 0x31ba) ||
      (c >= 0x31c0 && c <= 0x31e3) ||
      (c >= 0x31f0 && c <= 0x321e) ||
      (c >= 0x3220 && c <= 0x3247) ||
      (c >= 0x3250 && c <= 0x32fe) ||
      (c >= 0x3300 && c <= 0x4dbf) ||
      (c >= 0x4e00 && c <= 0xa48c) ||
      (c >= 0xa490 && c <= 0xa4c6) ||
      (c >= 0xa960 && c <= 0xa97c) ||
      (c >= 0xac00 && c <= 0xd7a3) ||
      (c >= 0xd7b0 && c <= 0xd7c6) ||
      (c >= 0xd7cb && c <= 0xd7fb) ||
      (c >= 0xf900 && c <= 0xfaff) ||
      (c >= 0xfe10 && c <= 0xfe19) ||
      (c >= 0xfe30 && c <= 0xfe52) ||
      (c >= 0xfe54 && c <= 0xfe66) ||
      (c >= 0xfe68 && c <= 0xfe6b) ||
      (c >= 0xff01 && c <= 0xff60) ||
      (c >= 0xffe0 && c <= 0xffe6)
    );
  }
  require("./edit_session/folding").Folding.call(EditSession.prototype);
  require("./edit_session/bracket_match").BracketMatch.call(
    EditSession.prototype,
  );
  config.defineOptions(EditSession.prototype, "session", {
    wrap: {
      set: function (value) {
        if (!value || value == "off") value = false;
        else if (value == "free") value = true;
        else if (value == "printMargin") value = -1;
        else if (typeof value == "string") value = parseInt(value, 10) || false;
        if (this.$wrap == value) return;
        this.$wrap = value;
        if (!value) {
          this.setUseWrapMode(false);
        } else {
          var col = typeof value == "number" ? value : null;
          this.setWrapLimitRange(col, col);
          this.setUseWrapMode(true);
        }
      },
      get: function () {
        if (this.getUseWrapMode()) {
          if (this.$wrap == -1) return "printMargin";
          if (!this.getWrapLimitRange().min) return "free";
          return this.$wrap;
        }
        return "off";
      },
      handlesSet: true,
    },
    wrapMethod: {
      set: function (val) {
        val = val == "auto" ? this.$mode.type != "text" : val != "text";
        if (val != this.$wrapAsCode) {
          this.$wrapAsCode = val;
          if (this.$useWrapMode) {
            this.$useWrapMode = false;
            this.setUseWrapMode(true);
          }
        }
      },
      initialValue: "auto",
    },
    indentedSoftWrap: {
      set: function () {
        if (this.$useWrapMode) {
          this.$useWrapMode = false;
          this.setUseWrapMode(true);
        }
      },
      initialValue: true,
    },
    firstLineNumber: {
      set: function () {
        this._signal("changeBreakpoint");
      },
      initialValue: 1,
    },
    useWorker: {
      set: function (useWorker) {
        this.$useWorker = useWorker;
        this.$stopWorker();
        if (useWorker) this.$startWorker();
      },
      initialValue: true,
    },
    useSoftTabs: { initialValue: true },
    tabSize: {
      set: function (tabSize) {
        tabSize = parseInt(tabSize);
        if (tabSize > 0 && this.$tabSize !== tabSize) {
          this.$modified = true;
          this.$rowLengthCache = [];
          this.$tabSize = tabSize;
          this._signal("changeTabSize");
        }
      },
      initialValue: 4,
      handlesSet: true,
    },
    navigateWithinSoftTabs: { initialValue: false },
    foldStyle: {
      set: function (val) {
        this.setFoldStyle(val);
      },
      handlesSet: true,
    },
    overwrite: {
      set: function (val) {
        this._signal("changeOverwrite");
      },
      initialValue: false,
    },
    newLineMode: {
      set: function (val) {
        this.doc.setNewLineMode(val);
      },
      get: function () {
        return this.doc.getNewLineMode();
      },
      handlesSet: true,
    },
    mode: {
      set: function (val) {
        this.setMode(val);
      },
      get: function () {
        return this.$modeId;
      },
      handlesSet: true,
    },
  });
  exports.EditSession = EditSession;
});

define("ace/search", [
  "require",
  "exports",
  "module",
  "ace/lib/lang",
  "ace/lib/oop",
  "ace/range",
], function (require, exports, module) {
  "use strict";
  var lang = require("./lib/lang");
  var oop = require("./lib/oop");
  var Range = require("./range").Range;
  var Search = /** @class */ (function () {
    function Search() {
      this.$options = {};
    }
    Search.prototype.set = function (options) {
      oop.mixin(this.$options, options);
      return this;
    };
    Search.prototype.getOptions = function () {
      return lang.copyObject(this.$options);
    };
    Search.prototype.setOptions = function (options) {
      this.$options = options;
    };
    Search.prototype.find = function (session) {
      var options = this.$options;
      var iterator = this.$matchIterator(session, options);
      if (!iterator) return false;
      var firstRange = null;
      iterator.forEach(function (sr, sc, er, ec) {
        firstRange = new Range(sr, sc, er, ec);
        if (
          sc == ec &&
          options.start &&
          /**@type{Range}*/ (options.start).start &&
          options.skipCurrent != false &&
          firstRange.isEqual(/**@type{Range}*/ (options.start))
        ) {
          firstRange = null;
          return false;
        }
        return true;
      });
      return firstRange;
    };
    Search.prototype.findAll = function (session) {
      var options = this.$options;
      if (!options.needle) return [];
      this.$assembleRegExp(options);
      var range = options.range;
      var lines = range
        ? session.getLines(range.start.row, range.end.row)
        : session.doc.getAllLines();
      var ranges = [];
      var re = options.re;
      if (options.$isMultiLine) {
        var len = re.length;
        var maxRow = lines.length - len;
        var prevRange;
        outer: for (var row = re.offset || 0; row <= maxRow; row++) {
          for (var j = 0; j < len; j++)
            if (lines[row + j].search(re[j]) == -1) continue outer;
          var startLine = lines[row];
          var line = lines[row + len - 1];
          var startIndex = startLine.length - startLine.match(re[0])[0].length;
          var endIndex = line.match(re[len - 1])[0].length;
          if (
            prevRange &&
            prevRange.end.row === row &&
            prevRange.end.column > startIndex
          ) {
            continue;
          }
          ranges.push(
            (prevRange = new Range(row, startIndex, row + len - 1, endIndex)),
          );
          if (len > 2) row = row + len - 2;
        }
      } else {
        for (var i = 0; i < lines.length; i++) {
          var matches = lang.getMatchOffsets(lines[i], re);
          for (var j = 0; j < matches.length; j++) {
            var match = matches[j];
            ranges.push(
              new Range(i, match.offset, i, match.offset + match.length),
            );
          }
        }
      }
      if (range) {
        var startColumn = range.start.column;
        var endColumn = range.end.column;
        var i = 0,
          j = ranges.length - 1;
        while (
          i < j &&
          ranges[i].start.column < startColumn &&
          ranges[i].start.row == 0
        )
          i++;
        var endRow = range.end.row - range.start.row;
        while (
          i < j &&
          ranges[j].end.column > endColumn &&
          ranges[j].end.row == endRow
        )
          j--;
        ranges = ranges.slice(i, j + 1);
        for (i = 0, j = ranges.length; i < j; i++) {
          ranges[i].start.row += range.start.row;
          ranges[i].end.row += range.start.row;
        }
      }
      return ranges;
    };
    Search.prototype.replace = function (input, replacement) {
      var options = this.$options;
      var re = this.$assembleRegExp(options);
      if (options.$isMultiLine) return replacement;
      if (!re) return;
      var match = re.exec(input);
      if (!match || match[0].length != input.length) return null;
      replacement = input.replace(re, replacement);
      if (options.preserveCase) {
        replacement = replacement.split("");
        for (var i = Math.min(input.length, input.length); i--; ) {
          var ch = input[i];
          if (ch && ch.toLowerCase() != ch)
            replacement[i] = replacement[i].toUpperCase();
          else replacement[i] = replacement[i].toLowerCase();
        }
        replacement = replacement.join("");
      }
      return replacement;
    };
    Search.prototype.$assembleRegExp = function (
      options,
      $disableFakeMultiline,
    ) {
      if (options.needle instanceof RegExp)
        return (options.re = options.needle);
      var needle = options.needle;
      if (!options.needle) return (options.re = false);
      if (!options.regExp) needle = lang.escapeRegExp(needle);
      var modifier = options.caseSensitive ? "gm" : "gmi";
      try {
        new RegExp(needle, "u");
        options.$supportsUnicodeFlag = true;
        modifier += "u";
      } catch (e) {
        options.$supportsUnicodeFlag = false; //left for backward compatibility with previous versions for cases like /ab\{2}/gu
      }
      if (options.wholeWord) needle = addWordBoundary(needle, options);
      options.$isMultiLine = !$disableFakeMultiline && /[\n\r]/.test(needle);
      if (options.$isMultiLine)
        return (options.re = this.$assembleMultilineRegExp(needle, modifier));
      try {
        var re = new RegExp(needle, modifier);
      } catch (e) {
        re = false;
      }
      return (options.re = re);
    };
    Search.prototype.$assembleMultilineRegExp = function (needle, modifier) {
      var parts = needle.replace(/\r\n|\r|\n/g, "$\n^").split("\n");
      var re = [];
      for (var i = 0; i < parts.length; i++)
        try {
          re.push(new RegExp(parts[i], modifier));
        } catch (e) {
          return false;
        }
      return re;
    };
    Search.prototype.$matchIterator = function (session, options) {
      var re = this.$assembleRegExp(options);
      if (!re) return false;
      var backwards = options.backwards == true;
      var skipCurrent = options.skipCurrent != false;
      var supportsUnicodeFlag = re.unicode;
      var range = options.range;
      var start = options.start;
      if (!start)
        start = range
          ? range[backwards ? "end" : "start"]
          : session.selection.getRange();
      if (start.start)
        start = start[skipCurrent != backwards ? "end" : "start"];
      var firstRow = range ? range.start.row : 0;
      var lastRow = range ? range.end.row : session.getLength() - 1;
      if (backwards) {
        var forEach = function (callback) {
          var row = start.row;
          if (forEachInLine(row, start.column, callback)) return;
          for (row--; row >= firstRow; row--)
            if (forEachInLine(row, Number.MAX_VALUE, callback)) return;
          if (options.wrap == false) return;
          for (row = lastRow, firstRow = start.row; row >= firstRow; row--)
            if (forEachInLine(row, Number.MAX_VALUE, callback)) return;
        };
      } else {
        var forEach = function (callback) {
          var row = start.row;
          if (forEachInLine(row, start.column, callback)) return;
          for (row = row + 1; row <= lastRow; row++)
            if (forEachInLine(row, 0, callback)) return;
          if (options.wrap == false) return;
          for (row = firstRow, lastRow = start.row; row <= lastRow; row++)
            if (forEachInLine(row, 0, callback)) return;
        };
      }
      if (options.$isMultiLine) {
        var len = re.length;
        var forEachInLine = function (row, offset, callback) {
          var startRow = backwards ? row - len + 1 : row;
          if (startRow < 0 || startRow + len > session.getLength()) return;
          var line = session.getLine(startRow);
          var startIndex = line.search(re[0]);
          if ((!backwards && startIndex < offset) || startIndex === -1) return;
          for (var i = 1; i < len; i++) {
            line = session.getLine(startRow + i);
            if (line.search(re[i]) == -1) return;
          }
          var endIndex = line.match(re[len - 1])[0].length;
          if (backwards && endIndex > offset) return;
          if (callback(startRow, startIndex, startRow + len - 1, endIndex))
            return true;
        };
      } else if (backwards) {
        var forEachInLine = function (row, endIndex, callback) {
          var line = session.getLine(row);
          var matches = [];
          var m,
            last = 0;
          re.lastIndex = 0;
          while ((m = re.exec(line))) {
            var length = m[0].length;
            last = m.index;
            if (!length) {
              if (last >= line.length) break;
              re.lastIndex = last += lang.skipEmptyMatch(
                line,
                last,
                supportsUnicodeFlag,
              );
            }
            if (m.index + length > endIndex) break;
            matches.push(m.index, length);
          }
          for (var i = matches.length - 1; i >= 0; i -= 2) {
            var column = matches[i - 1];
            var length = matches[i];
            if (callback(row, column, row, column + length)) return true;
          }
        };
      } else {
        var forEachInLine = function (row, startIndex, callback) {
          var line = session.getLine(row);
          var last;
          var m;
          re.lastIndex = startIndex;
          while ((m = re.exec(line))) {
            var length = m[0].length;
            last = m.index;
            if (callback(row, last, row, last + length)) return true;
            if (!length) {
              re.lastIndex = last += lang.skipEmptyMatch(
                line,
                last,
                supportsUnicodeFlag,
              );
              if (last >= line.length) return false;
            }
          }
        };
      }
      return { forEach: forEach };
    };
    return Search;
  })();
  function addWordBoundary(needle, options) {
    var supportsLookbehind = lang.supportsLookbehind();
    function wordBoundary(c, firstChar) {
      if (firstChar === void 0) {
        firstChar = true;
      }
      var wordRegExp =
        supportsLookbehind && options.$supportsUnicodeFlag
          ? new RegExp("[\\p{L}\\p{N}_]", "u")
          : new RegExp("\\w");
      if (wordRegExp.test(c) || options.regExp) {
        if (supportsLookbehind && options.$supportsUnicodeFlag) {
          if (firstChar) return "(?<=^|[^\\p{L}\\p{N}_])";
          return "(?=[^\\p{L}\\p{N}_]|$)";
        }
        return "\\b";
      }
      return "";
    }
    var needleArray = Array.from(needle);
    var firstChar = needleArray[0];
    var lastChar = needleArray[needleArray.length - 1];
    return wordBoundary(firstChar) + needle + wordBoundary(lastChar, false);
  }
  exports.Search = Search;
});

define("ace/keyboard/hash_handler", [
  "require",
  "exports",
  "module",
  "ace/lib/keys",
  "ace/lib/useragent",
], function (require, exports, module) {
  "use strict";
  var __extends =
    (this && this.__extends) ||
    (function () {
      var extendStatics = function (d, b) {
        extendStatics =
          Object.setPrototypeOf ||
          ({ __proto__: [] } instanceof Array &&
            function (d, b) {
              d.__proto__ = b;
            }) ||
          function (d, b) {
            for (var p in b)
              if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p];
          };
        return extendStatics(d, b);
      };
      return function (d, b) {
        if (typeof b !== "function" && b !== null)
          throw new TypeError(
            "Class extends value " +
              String(b) +
              " is not a constructor or null",
          );
        extendStatics(d, b);
        function __() {
          this.constructor = d;
        }
        d.prototype =
          b === null
            ? Object.create(b)
            : ((__.prototype = b.prototype), new __());
      };
    })();
  var keyUtil = require("../lib/keys");
  var useragent = require("../lib/useragent");
  var KEY_MODS = keyUtil.KEY_MODS;
  var MultiHashHandler = /** @class */ (function () {
    function MultiHashHandler(config, platform) {
      this.$init(config, platform, false);
    }
    MultiHashHandler.prototype.$init = function (
      config,
      platform,
      $singleCommand,
    ) {
      this.platform = platform || (useragent.isMac ? "mac" : "win");
      this.commands = {};
      this.commandKeyBinding = {};
      this.addCommands(config);
      this.$singleCommand = $singleCommand;
    };
    MultiHashHandler.prototype.addCommand = function (command) {
      if (this.commands[command.name]) this.removeCommand(command);
      this.commands[command.name] = command;
      if (command.bindKey) this._buildKeyHash(command);
    };
    MultiHashHandler.prototype.removeCommand = function (command, keepCommand) {
      var name =
        command && (typeof command === "string" ? command : command.name);
      command = this.commands[name];
      if (!keepCommand) delete this.commands[name];
      var ckb = this.commandKeyBinding;
      for (var keyId in ckb) {
        var cmdGroup = ckb[keyId];
        if (cmdGroup == command) {
          delete ckb[keyId];
        } else if (Array.isArray(cmdGroup)) {
          var i = cmdGroup.indexOf(command);
          if (i != -1) {
            cmdGroup.splice(i, 1);
            if (cmdGroup.length == 1) ckb[keyId] = cmdGroup[0];
          }
        }
      }
    };
    MultiHashHandler.prototype.bindKey = function (key, command, position) {
      if (typeof key == "object" && key) {
        if (position == undefined) position = key.position;
        key = key[this.platform];
      }
      if (!key) return;
      if (typeof command == "function")
        return this.addCommand({
          exec: command,
          bindKey: key,
          name: command.name || /**@type{string}*/ (key),
        });
      key.split("|").forEach(function (keyPart) {
        var chain = "";
        if (keyPart.indexOf(" ") != -1) {
          var parts = keyPart.split(/\s+/);
          keyPart = parts.pop();
          parts.forEach(function (keyPart) {
            var binding = this.parseKeys(keyPart);
            var id = KEY_MODS[binding.hashId] + binding.key;
            chain += (chain ? " " : "") + id;
            this._addCommandToBinding(chain, "chainKeys");
          }, this);
          chain += " ";
        }
        var binding = this.parseKeys(keyPart);
        var id = KEY_MODS[binding.hashId] + binding.key;
        this._addCommandToBinding(chain + id, command, position);
      }, this);
    };
    MultiHashHandler.prototype._addCommandToBinding = function (
      keyId,
      command,
      position,
    ) {
      var ckb = this.commandKeyBinding,
        i;
      if (!command) {
        delete ckb[keyId];
      } else if (!ckb[keyId] || this.$singleCommand) {
        ckb[keyId] = command;
      } else {
        if (!Array.isArray(ckb[keyId])) {
          ckb[keyId] = [ckb[keyId]];
        } else if ((i = ckb[keyId].indexOf(command)) != -1) {
          ckb[keyId].splice(i, 1);
        }
        if (typeof position != "number") {
          position = getPosition(command);
        }
        var commands = ckb[keyId];
        for (i = 0; i < commands.length; i++) {
          var other = commands[i];
          var otherPos = getPosition(other);
          if (otherPos > position) break;
        }
        commands.splice(i, 0, command);
      }
    };
    MultiHashHandler.prototype.addCommands = function (commands) {
      commands &&
        Object.keys(commands).forEach(function (name) {
          var command = commands[name];
          if (!command) return;
          if (typeof command === "string") return this.bindKey(command, name);
          if (typeof command === "function") command = { exec: command };
          if (typeof command !== "object") return;
          if (!command.name) command.name = name;
          this.addCommand(command);
        }, this);
    };
    MultiHashHandler.prototype.removeCommands = function (commands) {
      Object.keys(commands).forEach(function (name) {
        this.removeCommand(commands[name]);
      }, this);
    };
    MultiHashHandler.prototype.bindKeys = function (keyList) {
      Object.keys(keyList).forEach(function (key) {
        this.bindKey(key, keyList[key]);
      }, this);
    };
    MultiHashHandler.prototype._buildKeyHash = function (command) {
      this.bindKey(command.bindKey, command);
    };
    MultiHashHandler.prototype.parseKeys = function (keys) {
      var parts = keys
        .toLowerCase()
        .split(/[\-\+]([\-\+])?/)
        .filter(function (x) {
          return x;
        });
      var key = parts.pop();
      var keyCode = keyUtil[key];
      if (keyUtil.FUNCTION_KEYS[keyCode])
        key = keyUtil.FUNCTION_KEYS[keyCode].toLowerCase();
      else if (!parts.length) return { key: key, hashId: -1 };
      else if (parts.length == 1 && parts[0] == "shift")
        return { key: key.toUpperCase(), hashId: -1 };
      var hashId = 0;
      for (var i = parts.length; i--; ) {
        var modifier = keyUtil.KEY_MODS[parts[i]];
        if (modifier == null) {
          if (typeof console != "undefined")
            console.error("invalid modifier " + parts[i] + " in " + keys);
          return false;
        }
        hashId |= modifier;
      }
      return { key: key, hashId: hashId };
    };
    MultiHashHandler.prototype.findKeyCommand = function (hashId, keyString) {
      var key = KEY_MODS[hashId] + keyString;
      return this.commandKeyBinding[key];
    };
    MultiHashHandler.prototype.handleKeyboard = function (
      data,
      hashId,
      keyString,
      keyCode,
    ) {
      if (keyCode < 0) return;
      var key = KEY_MODS[hashId] + keyString;
      var command = this.commandKeyBinding[key];
      if (data.$keyChain) {
        data.$keyChain += " " + key;
        command = this.commandKeyBinding[data.$keyChain] || command;
      }
      if (command) {
        if (
          command == "chainKeys" ||
          command[command.length - 1] == "chainKeys"
        ) {
          data.$keyChain = data.$keyChain || key;
          return { command: "null" };
        }
      }
      if (data.$keyChain) {
        if ((!hashId || hashId == 4) && keyString.length == 1)
          data.$keyChain = data.$keyChain.slice(
            0,
            -key.length - 1,
          ); // wait for input
        else if (hashId == -1 || keyCode > 0) data.$keyChain = ""; // reset keyChain
      }
      return { command: command };
    };
    MultiHashHandler.prototype.getStatusText = function (editor, data) {
      return data.$keyChain || "";
    };
    return MultiHashHandler;
  })();
  function getPosition(command) {
    return (
      (typeof command == "object" &&
        command.bindKey &&
        command.bindKey.position) ||
      (command.isDefault ? -100 : 0)
    );
  }
  var HashHandler = /** @class */ (function (_super) {
    __extends(HashHandler, _super);
    function HashHandler(config, platform) {
      var _this = _super.call(this, config, platform) || this;
      _this.$singleCommand = true;
      return _this;
    }
    return HashHandler;
  })(MultiHashHandler);
  HashHandler.call = function (thisArg, config, platform) {
    MultiHashHandler.prototype.$init.call(thisArg, config, platform, true);
  };
  MultiHashHandler.call = function (thisArg, config, platform) {
    MultiHashHandler.prototype.$init.call(thisArg, config, platform, false);
  };
  exports.HashHandler = HashHandler;
  exports.MultiHashHandler = MultiHashHandler;
});

define("ace/commands/command_manager", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/keyboard/hash_handler",
  "ace/lib/event_emitter",
], function (require, exports, module) {
  "use strict";
  var __extends =
    (this && this.__extends) ||
    (function () {
      var extendStatics = function (d, b) {
        extendStatics =
          Object.setPrototypeOf ||
          ({ __proto__: [] } instanceof Array &&
            function (d, b) {
              d.__proto__ = b;
            }) ||
          function (d, b) {
            for (var p in b)
              if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p];
          };
        return extendStatics(d, b);
      };
      return function (d, b) {
        if (typeof b !== "function" && b !== null)
          throw new TypeError(
            "Class extends value " +
              String(b) +
              " is not a constructor or null",
          );
        extendStatics(d, b);
        function __() {
          this.constructor = d;
        }
        d.prototype =
          b === null
            ? Object.create(b)
            : ((__.prototype = b.prototype), new __());
      };
    })();
  var oop = require("../lib/oop");
  var MultiHashHandler = require("../keyboard/hash_handler").MultiHashHandler;
  var EventEmitter = require("../lib/event_emitter").EventEmitter;
  var CommandManager = /** @class */ (function (_super) {
    __extends(CommandManager, _super);
    function CommandManager(platform, commands) {
      var _this = _super.call(this, commands, platform) || this;
      _this.byName = _this.commands;
      _this.setDefaultHandler("exec", function (e) {
        if (!e.args) {
          return e.command.exec(e.editor, {}, e.event, true);
        }
        return e.command.exec(e.editor, e.args, e.event, false);
      });
      return _this;
    }
    CommandManager.prototype.exec = function (command, editor, args) {
      if (Array.isArray(command)) {
        for (var i = command.length; i--; ) {
          if (this.exec(command[i], editor, args)) return true;
        }
        return false;
      }
      if (typeof command === "string") command = this.commands[command];
      if (!command) return false;
      if (editor && editor.$readOnly && !command.readOnly) return false;
      if (
        this.$checkCommandState != false &&
        command.isAvailable &&
        !command.isAvailable(editor)
      )
        return false;
      var e = { editor: editor, command: command, args: args };
      e.returnValue = this._emit("exec", e);
      this._signal("afterExec", e);
      return e.returnValue === false ? false : true;
    };
    CommandManager.prototype.toggleRecording = function (editor) {
      if (this.$inReplay) return;
      editor && editor._emit("changeStatus");
      if (this.recording) {
        this.macro.pop();
        this.off("exec", this.$addCommandToMacro);
        if (!this.macro.length) this.macro = this.oldMacro;
        return (this.recording = false);
      }
      if (!this.$addCommandToMacro) {
        this.$addCommandToMacro = function (e) {
          this.macro.push([e.command, e.args]);
        }.bind(this);
      }
      this.oldMacro = this.macro;
      this.macro = [];
      this.on("exec", this.$addCommandToMacro);
      return (this.recording = true);
    };
    CommandManager.prototype.replay = function (editor) {
      if (this.$inReplay || !this.macro) return;
      if (this.recording) return this.toggleRecording(editor);
      try {
        this.$inReplay = true;
        this.macro.forEach(function (x) {
          if (typeof x == "string") this.exec(x, editor);
          else this.exec(x[0], editor, x[1]);
        }, this);
      } finally {
        this.$inReplay = false;
      }
    };
    CommandManager.prototype.trimMacro = function (m) {
      return m.map(function (x) {
        if (typeof x[0] != "string") x[0] = x[0].name;
        if (!x[1]) x = x[0];
        return x;
      });
    };
    return CommandManager;
  })(MultiHashHandler);
  oop.implement(CommandManager.prototype, EventEmitter);
  exports.CommandManager = CommandManager;
});

define("ace/commands/default_commands", [
  "require",
  "exports",
  "module",
  "ace/lib/lang",
  "ace/config",
  "ace/range",
], function (require, exports, module) {
  "use strict";
  var lang = require("../lib/lang");
  var config = require("../config");
  var Range = require("../range").Range;
  function bindKey(win, mac) {
    return { win: win, mac: mac };
  }
  exports.commands = [
    {
      name: "showSettingsMenu",
      description: "Show settings menu",
      bindKey: bindKey("Ctrl-,", "Command-,"),
      exec: function (editor) {
        config.loadModule("ace/ext/settings_menu", function (module) {
          module.init(editor);
          editor.showSettingsMenu();
        });
      },
      readOnly: true,
    },
    {
      name: "goToNextError",
      description: "Go to next error",
      bindKey: bindKey("Alt-E", "F4"),
      exec: function (editor) {
        config.loadModule("ace/ext/error_marker", function (module) {
          module.showErrorMarker(editor, 1);
        });
      },
      scrollIntoView: "animate",
      readOnly: true,
    },
    {
      name: "goToPreviousError",
      description: "Go to previous error",
      bindKey: bindKey("Alt-Shift-E", "Shift-F4"),
      exec: function (editor) {
        config.loadModule("ace/ext/error_marker", function (module) {
          module.showErrorMarker(editor, -1);
        });
      },
      scrollIntoView: "animate",
      readOnly: true,
    },
    {
      name: "selectall",
      description: "Select all",
      bindKey: bindKey("Ctrl-A", "Command-A"),
      exec: function (editor) {
        editor.selectAll();
      },
      readOnly: true,
    },
    {
      name: "centerselection",
      description: "Center selection",
      bindKey: bindKey(null, "Ctrl-L"),
      exec: function (editor) {
        editor.centerSelection();
      },
      readOnly: true,
    },
    {
      name: "gotoline",
      description: "Go to line...",
      bindKey: bindKey("Ctrl-L", "Command-L"),
      exec: function (editor, line) {
        if (typeof line === "number" && !isNaN(line)) editor.gotoLine(line);
        editor.prompt({ $type: "gotoLine" });
      },
      readOnly: true,
    },
    {
      name: "fold",
      bindKey: bindKey("Alt-L|Ctrl-F1", "Command-Alt-L|Command-F1"),
      exec: function (editor) {
        editor.session.toggleFold(false);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "center",
      readOnly: true,
    },
    {
      name: "unfold",
      bindKey: bindKey(
        "Alt-Shift-L|Ctrl-Shift-F1",
        "Command-Alt-Shift-L|Command-Shift-F1",
      ),
      exec: function (editor) {
        editor.session.toggleFold(true);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "center",
      readOnly: true,
    },
    {
      name: "toggleFoldWidget",
      description: "Toggle fold widget",
      bindKey: bindKey("F2", "F2"),
      exec: function (editor) {
        editor.session.toggleFoldWidget();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "center",
      readOnly: true,
    },
    {
      name: "toggleParentFoldWidget",
      description: "Toggle parent fold widget",
      bindKey: bindKey("Alt-F2", "Alt-F2"),
      exec: function (editor) {
        editor.session.toggleFoldWidget(true);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "center",
      readOnly: true,
    },
    {
      name: "foldall",
      description: "Fold all",
      bindKey: bindKey(null, "Ctrl-Command-Option-0"),
      exec: function (editor) {
        editor.session.foldAll();
      },
      scrollIntoView: "center",
      readOnly: true,
    },
    {
      name: "foldAllComments",
      description: "Fold all comments",
      bindKey: bindKey(null, "Ctrl-Command-Option-0"),
      exec: function (editor) {
        editor.session.foldAllComments();
      },
      scrollIntoView: "center",
      readOnly: true,
    },
    {
      name: "foldOther",
      description: "Fold other",
      bindKey: bindKey("Alt-0", "Command-Option-0"),
      exec: function (editor) {
        editor.session.foldAll();
        editor.session.unfold(editor.selection.getAllRanges());
      },
      scrollIntoView: "center",
      readOnly: true,
    },
    {
      name: "unfoldall",
      description: "Unfold all",
      bindKey: bindKey("Alt-Shift-0", "Command-Option-Shift-0"),
      exec: function (editor) {
        editor.session.unfold();
      },
      scrollIntoView: "center",
      readOnly: true,
    },
    {
      name: "findnext",
      description: "Find next",
      bindKey: bindKey("Ctrl-K", "Command-G"),
      exec: function (editor) {
        editor.findNext();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "center",
      readOnly: true,
    },
    {
      name: "findprevious",
      description: "Find previous",
      bindKey: bindKey("Ctrl-Shift-K", "Command-Shift-G"),
      exec: function (editor) {
        editor.findPrevious();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "center",
      readOnly: true,
    },
    {
      name: "selectOrFindNext",
      description: "Select or find next",
      bindKey: bindKey("Alt-K", "Ctrl-G"),
      exec: function (editor) {
        if (editor.selection.isEmpty()) editor.selection.selectWord();
        else editor.findNext();
      },
      readOnly: true,
    },
    {
      name: "selectOrFindPrevious",
      description: "Select or find previous",
      bindKey: bindKey("Alt-Shift-K", "Ctrl-Shift-G"),
      exec: function (editor) {
        if (editor.selection.isEmpty()) editor.selection.selectWord();
        else editor.findPrevious();
      },
      readOnly: true,
    },
    {
      name: "find",
      description: "Find",
      bindKey: bindKey("Ctrl-F", "Command-F"),
      exec: function (editor) {
        config.loadModule("ace/ext/searchbox", function (e) {
          e.Search(editor);
        });
      },
      readOnly: true,
    },
    {
      name: "overwrite",
      description: "Overwrite",
      bindKey: "Insert",
      exec: function (editor) {
        editor.toggleOverwrite();
      },
      readOnly: true,
    },
    {
      name: "selecttostart",
      description: "Select to start",
      bindKey: bindKey(
        "Ctrl-Shift-Home",
        "Command-Shift-Home|Command-Shift-Up",
      ),
      exec: function (editor) {
        editor.getSelection().selectFileStart();
      },
      multiSelectAction: "forEach",
      readOnly: true,
      scrollIntoView: "animate",
      aceCommandGroup: "fileJump",
    },
    {
      name: "gotostart",
      description: "Go to start",
      bindKey: bindKey("Ctrl-Home", "Command-Home|Command-Up"),
      exec: function (editor) {
        editor.navigateFileStart();
      },
      multiSelectAction: "forEach",
      readOnly: true,
      scrollIntoView: "animate",
      aceCommandGroup: "fileJump",
    },
    {
      name: "selectup",
      description: "Select up",
      bindKey: bindKey("Shift-Up", "Shift-Up|Ctrl-Shift-P"),
      exec: function (editor) {
        editor.getSelection().selectUp();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "golineup",
      description: "Go line up",
      bindKey: bindKey("Up", "Up|Ctrl-P"),
      exec: function (editor, args) {
        editor.navigateUp(args.times);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selecttoend",
      description: "Select to end",
      bindKey: bindKey(
        "Ctrl-Shift-End",
        "Command-Shift-End|Command-Shift-Down",
      ),
      exec: function (editor) {
        editor.getSelection().selectFileEnd();
      },
      multiSelectAction: "forEach",
      readOnly: true,
      scrollIntoView: "animate",
      aceCommandGroup: "fileJump",
    },
    {
      name: "gotoend",
      description: "Go to end",
      bindKey: bindKey("Ctrl-End", "Command-End|Command-Down"),
      exec: function (editor) {
        editor.navigateFileEnd();
      },
      multiSelectAction: "forEach",
      readOnly: true,
      scrollIntoView: "animate",
      aceCommandGroup: "fileJump",
    },
    {
      name: "selectdown",
      description: "Select down",
      bindKey: bindKey("Shift-Down", "Shift-Down|Ctrl-Shift-N"),
      exec: function (editor) {
        editor.getSelection().selectDown();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "golinedown",
      description: "Go line down",
      bindKey: bindKey("Down", "Down|Ctrl-N"),
      exec: function (editor, args) {
        editor.navigateDown(args.times);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selectwordleft",
      description: "Select word left",
      bindKey: bindKey("Ctrl-Shift-Left", "Option-Shift-Left"),
      exec: function (editor) {
        editor.getSelection().selectWordLeft();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "gotowordleft",
      description: "Go to word left",
      bindKey: bindKey("Ctrl-Left", "Option-Left"),
      exec: function (editor) {
        editor.navigateWordLeft();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selecttolinestart",
      description: "Select to line start",
      bindKey: bindKey("Alt-Shift-Left", "Command-Shift-Left|Ctrl-Shift-A"),
      exec: function (editor) {
        editor.getSelection().selectLineStart();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "gotolinestart",
      description: "Go to line start",
      bindKey: bindKey("Alt-Left|Home", "Command-Left|Home|Ctrl-A"),
      exec: function (editor) {
        editor.navigateLineStart();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selectleft",
      description: "Select left",
      bindKey: bindKey("Shift-Left", "Shift-Left|Ctrl-Shift-B"),
      exec: function (editor) {
        editor.getSelection().selectLeft();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "gotoleft",
      description: "Go to left",
      bindKey: bindKey("Left", "Left|Ctrl-B"),
      exec: function (editor, args) {
        editor.navigateLeft(args.times);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selectwordright",
      description: "Select word right",
      bindKey: bindKey("Ctrl-Shift-Right", "Option-Shift-Right"),
      exec: function (editor) {
        editor.getSelection().selectWordRight();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "gotowordright",
      description: "Go to word right",
      bindKey: bindKey("Ctrl-Right", "Option-Right"),
      exec: function (editor) {
        editor.navigateWordRight();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selecttolineend",
      description: "Select to line end",
      bindKey: bindKey(
        "Alt-Shift-Right",
        "Command-Shift-Right|Shift-End|Ctrl-Shift-E",
      ),
      exec: function (editor) {
        editor.getSelection().selectLineEnd();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "gotolineend",
      description: "Go to line end",
      bindKey: bindKey("Alt-Right|End", "Command-Right|End|Ctrl-E"),
      exec: function (editor) {
        editor.navigateLineEnd();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selectright",
      description: "Select right",
      bindKey: bindKey("Shift-Right", "Shift-Right"),
      exec: function (editor) {
        editor.getSelection().selectRight();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "gotoright",
      description: "Go to right",
      bindKey: bindKey("Right", "Right|Ctrl-F"),
      exec: function (editor, args) {
        editor.navigateRight(args.times);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selectpagedown",
      description: "Select page down",
      bindKey: "Shift-PageDown",
      exec: function (editor) {
        editor.selectPageDown();
      },
      readOnly: true,
    },
    {
      name: "pagedown",
      description: "Page down",
      bindKey: bindKey(null, "Option-PageDown"),
      exec: function (editor) {
        editor.scrollPageDown();
      },
      readOnly: true,
    },
    {
      name: "gotopagedown",
      description: "Go to page down",
      bindKey: bindKey("PageDown", "PageDown|Ctrl-V"),
      exec: function (editor) {
        editor.gotoPageDown();
      },
      readOnly: true,
    },
    {
      name: "selectpageup",
      description: "Select page up",
      bindKey: "Shift-PageUp",
      exec: function (editor) {
        editor.selectPageUp();
      },
      readOnly: true,
    },
    {
      name: "pageup",
      description: "Page up",
      bindKey: bindKey(null, "Option-PageUp"),
      exec: function (editor) {
        editor.scrollPageUp();
      },
      readOnly: true,
    },
    {
      name: "gotopageup",
      description: "Go to page up",
      bindKey: "PageUp",
      exec: function (editor) {
        editor.gotoPageUp();
      },
      readOnly: true,
    },
    {
      name: "scrollup",
      description: "Scroll up",
      bindKey: bindKey("Ctrl-Up", null),
      exec: function (e) {
        e.renderer.scrollBy(0, -2 * e.renderer.layerConfig.lineHeight);
      },
      readOnly: true,
    },
    {
      name: "scrolldown",
      description: "Scroll down",
      bindKey: bindKey("Ctrl-Down", null),
      exec: function (e) {
        e.renderer.scrollBy(0, 2 * e.renderer.layerConfig.lineHeight);
      },
      readOnly: true,
    },
    {
      name: "selectlinestart",
      description: "Select line start",
      bindKey: "Shift-Home",
      exec: function (editor) {
        editor.getSelection().selectLineStart();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selectlineend",
      description: "Select line end",
      bindKey: "Shift-End",
      exec: function (editor) {
        editor.getSelection().selectLineEnd();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "togglerecording",
      description: "Toggle recording",
      bindKey: bindKey("Ctrl-Alt-E", "Command-Option-E"),
      exec: function (editor) {
        editor.commands.toggleRecording(editor);
      },
      readOnly: true,
    },
    {
      name: "replaymacro",
      description: "Replay macro",
      bindKey: bindKey("Ctrl-Shift-E", "Command-Shift-E"),
      exec: function (editor) {
        editor.commands.replay(editor);
      },
      readOnly: true,
    },
    {
      name: "jumptomatching",
      description: "Jump to matching",
      bindKey: bindKey("Ctrl-\\|Ctrl-P", "Command-\\"),
      exec: function (editor) {
        editor.jumpToMatching();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "animate",
      readOnly: true,
    },
    {
      name: "selecttomatching",
      description: "Select to matching",
      bindKey: bindKey("Ctrl-Shift-\\|Ctrl-Shift-P", "Command-Shift-\\"),
      exec: function (editor) {
        editor.jumpToMatching(true);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "animate",
      readOnly: true,
    },
    {
      name: "expandToMatching",
      description: "Expand to matching",
      bindKey: bindKey("Ctrl-Shift-M", "Ctrl-Shift-M"),
      exec: function (editor) {
        editor.jumpToMatching(true, true);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "animate",
      readOnly: true,
    },
    {
      name: "passKeysToBrowser",
      description: "Pass keys to browser",
      bindKey: bindKey(null, null),
      exec: function () {},
      passEvent: true,
      readOnly: true,
    },
    {
      name: "copy",
      description: "Copy",
      exec: function (editor) {},
      readOnly: true,
    },
    {
      name: "cut",
      description: "Cut",
      exec: function (editor) {
        var cutLine =
          editor.$copyWithEmptySelection && editor.selection.isEmpty();
        var range = cutLine
          ? editor.selection.getLineRange()
          : editor.selection.getRange();
        editor._emit("cut", range);
        if (!range.isEmpty()) editor.session.remove(range);
        editor.clearSelection();
      },
      scrollIntoView: "cursor",
      multiSelectAction: "forEach",
    },
    {
      name: "paste",
      description: "Paste",
      exec: function (editor, args) {
        editor.$handlePaste(args);
      },
      scrollIntoView: "cursor",
    },
    {
      name: "removeline",
      description: "Remove line",
      bindKey: bindKey("Ctrl-D", "Command-D"),
      exec: function (editor) {
        editor.removeLines();
      },
      scrollIntoView: "cursor",
      multiSelectAction: "forEachLine",
    },
    {
      name: "duplicateSelection",
      description: "Duplicate selection",
      bindKey: bindKey("Ctrl-Shift-D", "Command-Shift-D"),
      exec: function (editor) {
        editor.duplicateSelection();
      },
      scrollIntoView: "cursor",
      multiSelectAction: "forEach",
    },
    {
      name: "sortlines",
      description: "Sort lines",
      bindKey: bindKey("Ctrl-Alt-S", "Command-Alt-S"),
      exec: function (editor) {
        editor.sortLines();
      },
      scrollIntoView: "selection",
      multiSelectAction: "forEachLine",
    },
    {
      name: "togglecomment",
      description: "Toggle comment",
      bindKey: bindKey("Ctrl-/", "Command-/"),
      exec: function (editor) {
        editor.toggleCommentLines();
      },
      multiSelectAction: "forEachLine",
      scrollIntoView: "selectionPart",
    },
    {
      name: "toggleBlockComment",
      description: "Toggle block comment",
      bindKey: bindKey("Ctrl-Shift-/", "Command-Shift-/"),
      exec: function (editor) {
        editor.toggleBlockComment();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "selectionPart",
    },
    {
      name: "modifyNumberUp",
      description: "Modify number up",
      bindKey: bindKey("Ctrl-Shift-Up", "Alt-Shift-Up"),
      exec: function (editor) {
        editor.modifyNumber(1);
      },
      scrollIntoView: "cursor",
      multiSelectAction: "forEach",
    },
    {
      name: "modifyNumberDown",
      description: "Modify number down",
      bindKey: bindKey("Ctrl-Shift-Down", "Alt-Shift-Down"),
      exec: function (editor) {
        editor.modifyNumber(-1);
      },
      scrollIntoView: "cursor",
      multiSelectAction: "forEach",
    },
    {
      name: "replace",
      description: "Replace",
      bindKey: bindKey("Ctrl-H", "Command-Option-F"),
      exec: function (editor) {
        config.loadModule("ace/ext/searchbox", function (e) {
          e.Search(editor, true);
        });
      },
    },
    {
      name: "undo",
      description: "Undo",
      bindKey: bindKey("Ctrl-Z", "Command-Z"),
      exec: function (editor) {
        editor.undo();
      },
    },
    {
      name: "redo",
      description: "Redo",
      bindKey: bindKey("Ctrl-Shift-Z|Ctrl-Y", "Command-Shift-Z|Command-Y"),
      exec: function (editor) {
        editor.redo();
      },
    },
    {
      name: "copylinesup",
      description: "Copy lines up",
      bindKey: bindKey("Alt-Shift-Up", "Command-Option-Up"),
      exec: function (editor) {
        editor.copyLinesUp();
      },
      scrollIntoView: "cursor",
    },
    {
      name: "movelinesup",
      description: "Move lines up",
      bindKey: bindKey("Alt-Up", "Option-Up"),
      exec: function (editor) {
        editor.moveLinesUp();
      },
      scrollIntoView: "cursor",
    },
    {
      name: "copylinesdown",
      description: "Copy lines down",
      bindKey: bindKey("Alt-Shift-Down", "Command-Option-Down"),
      exec: function (editor) {
        editor.copyLinesDown();
      },
      scrollIntoView: "cursor",
    },
    {
      name: "movelinesdown",
      description: "Move lines down",
      bindKey: bindKey("Alt-Down", "Option-Down"),
      exec: function (editor) {
        editor.moveLinesDown();
      },
      scrollIntoView: "cursor",
    },
    {
      name: "del",
      description: "Delete",
      bindKey: bindKey("Delete", "Delete|Ctrl-D|Shift-Delete"),
      exec: function (editor) {
        editor.remove("right");
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "backspace",
      description: "Backspace",
      bindKey: bindKey(
        "Shift-Backspace|Backspace",
        "Ctrl-Backspace|Shift-Backspace|Backspace|Ctrl-H",
      ),
      exec: function (editor) {
        editor.remove("left");
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "cut_or_delete",
      description: "Cut or delete",
      bindKey: bindKey("Shift-Delete", null),
      exec: function (editor) {
        if (editor.selection.isEmpty()) {
          editor.remove("left");
        } else {
          return false;
        }
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "removetolinestart",
      description: "Remove to line start",
      bindKey: bindKey("Alt-Backspace", "Command-Backspace"),
      exec: function (editor) {
        editor.removeToLineStart();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "removetolineend",
      description: "Remove to line end",
      bindKey: bindKey("Alt-Delete", "Ctrl-K|Command-Delete"),
      exec: function (editor) {
        editor.removeToLineEnd();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "removetolinestarthard",
      description: "Remove to line start hard",
      bindKey: bindKey("Ctrl-Shift-Backspace", null),
      exec: function (editor) {
        var range = editor.selection.getRange();
        range.start.column = 0;
        editor.session.remove(range);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "removetolineendhard",
      description: "Remove to line end hard",
      bindKey: bindKey("Ctrl-Shift-Delete", null),
      exec: function (editor) {
        var range = editor.selection.getRange();
        range.end.column = Number.MAX_VALUE;
        editor.session.remove(range);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "removewordleft",
      description: "Remove word left",
      bindKey: bindKey("Ctrl-Backspace", "Alt-Backspace|Ctrl-Alt-Backspace"),
      exec: function (editor) {
        editor.removeWordLeft();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "removewordright",
      description: "Remove word right",
      bindKey: bindKey("Ctrl-Delete", "Alt-Delete"),
      exec: function (editor) {
        editor.removeWordRight();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "outdent",
      description: "Outdent",
      bindKey: bindKey("Shift-Tab", "Shift-Tab"),
      exec: function (editor) {
        editor.blockOutdent();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "selectionPart",
    },
    {
      name: "indent",
      description: "Indent",
      bindKey: bindKey("Tab", "Tab"),
      exec: function (editor) {
        editor.indent();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "selectionPart",
    },
    {
      name: "blockoutdent",
      description: "Block outdent",
      bindKey: bindKey("Ctrl-[", "Ctrl-["),
      exec: function (editor) {
        editor.blockOutdent();
      },
      multiSelectAction: "forEachLine",
      scrollIntoView: "selectionPart",
    },
    {
      name: "blockindent",
      description: "Block indent",
      bindKey: bindKey("Ctrl-]", "Ctrl-]"),
      exec: function (editor) {
        editor.blockIndent();
      },
      multiSelectAction: "forEachLine",
      scrollIntoView: "selectionPart",
    },
    {
      name: "insertstring",
      description: "Insert string",
      exec: function (editor, str) {
        editor.insert(str);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "inserttext",
      description: "Insert text",
      exec: function (editor, args) {
        editor.insert(lang.stringRepeat(args.text || "", args.times || 1));
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "splitline",
      description: "Split line",
      bindKey: bindKey(null, "Ctrl-O"),
      exec: function (editor) {
        editor.splitLine();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "transposeletters",
      description: "Transpose letters",
      bindKey: bindKey("Alt-Shift-X", "Ctrl-T"),
      exec: function (editor) {
        editor.transposeLetters();
      },
      multiSelectAction: function (editor) {
        editor.transposeSelections(1);
      },
      scrollIntoView: "cursor",
    },
    {
      name: "touppercase",
      description: "To uppercase",
      bindKey: bindKey("Ctrl-U", "Ctrl-U"),
      exec: function (editor) {
        editor.toUpperCase();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "tolowercase",
      description: "To lowercase",
      bindKey: bindKey("Ctrl-Shift-U", "Ctrl-Shift-U"),
      exec: function (editor) {
        editor.toLowerCase();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "autoindent",
      description: "Auto Indent",
      bindKey: bindKey(null, null),
      exec: function (editor) {
        editor.autoIndent();
      },
      multiSelectAction: "forEachLine",
      scrollIntoView: "animate",
    },
    {
      name: "expandtoline",
      description: "Expand to line",
      bindKey: bindKey("Ctrl-Shift-L", "Command-Shift-L"),
      exec: function (editor) {
        var range = editor.selection.getRange();
        range.start.column = range.end.column = 0;
        range.end.row++;
        editor.selection.setRange(range, false);
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "openlink",
      bindKey: bindKey("Ctrl+F3", "F3"),
      exec: function (editor) {
        editor.openLink();
      },
    },
    {
      name: "joinlines",
      description: "Join lines",
      bindKey: bindKey(null, null),
      exec: function (editor) {
        var isBackwards = editor.selection.isBackwards();
        var selectionStart = isBackwards
          ? editor.selection.getSelectionLead()
          : editor.selection.getSelectionAnchor();
        var selectionEnd = isBackwards
          ? editor.selection.getSelectionAnchor()
          : editor.selection.getSelectionLead();
        var firstLineEndCol = editor.session.doc.getLine(
          selectionStart.row,
        ).length;
        var selectedText = editor.session.doc.getTextRange(
          editor.selection.getRange(),
        );
        var selectedCount = selectedText.replace(/\n\s*/, " ").length;
        var insertLine = editor.session.doc.getLine(selectionStart.row);
        for (var i = selectionStart.row + 1; i <= selectionEnd.row + 1; i++) {
          var curLine = lang.stringTrimLeft(
            lang.stringTrimRight(editor.session.doc.getLine(i)),
          );
          if (curLine.length !== 0) {
            curLine = " " + curLine;
          }
          insertLine += curLine;
        }
        if (selectionEnd.row + 1 < editor.session.doc.getLength() - 1) {
          insertLine += editor.session.doc.getNewLineCharacter();
        }
        editor.clearSelection();
        editor.session.doc.replace(
          new Range(selectionStart.row, 0, selectionEnd.row + 2, 0),
          insertLine,
        );
        if (selectedCount > 0) {
          editor.selection.moveCursorTo(
            selectionStart.row,
            selectionStart.column,
          );
          editor.selection.selectTo(
            selectionStart.row,
            selectionStart.column + selectedCount,
          );
        } else {
          firstLineEndCol =
            editor.session.doc.getLine(selectionStart.row).length >
            firstLineEndCol
              ? firstLineEndCol + 1
              : firstLineEndCol;
          editor.selection.moveCursorTo(selectionStart.row, firstLineEndCol);
        }
      },
      multiSelectAction: "forEach",
      readOnly: true,
    },
    {
      name: "invertSelection",
      description: "Invert selection",
      bindKey: bindKey(null, null),
      exec: function (editor) {
        var endRow = editor.session.doc.getLength() - 1;
        var endCol = editor.session.doc.getLine(endRow).length;
        var ranges = editor.selection.rangeList.ranges;
        var newRanges = [];
        if (ranges.length < 1) {
          ranges = [editor.selection.getRange()];
        }
        for (var i = 0; i < ranges.length; i++) {
          if (i == ranges.length - 1) {
            if (
              !(ranges[i].end.row === endRow && ranges[i].end.column === endCol)
            ) {
              newRanges.push(
                new Range(
                  ranges[i].end.row,
                  ranges[i].end.column,
                  endRow,
                  endCol,
                ),
              );
            }
          }
          if (i === 0) {
            if (!(ranges[i].start.row === 0 && ranges[i].start.column === 0)) {
              newRanges.push(
                new Range(0, 0, ranges[i].start.row, ranges[i].start.column),
              );
            }
          } else {
            newRanges.push(
              new Range(
                ranges[i - 1].end.row,
                ranges[i - 1].end.column,
                ranges[i].start.row,
                ranges[i].start.column,
              ),
            );
          }
        }
        editor.exitMultiSelectMode();
        editor.clearSelection();
        for (var i = 0; i < newRanges.length; i++) {
          editor.selection.addRange(newRanges[i], false);
        }
      },
      readOnly: true,
      scrollIntoView: "none",
    },
    {
      name: "addLineAfter",
      description: "Add new line after the current line",
      exec: function (editor) {
        editor.selection.clearSelection();
        editor.navigateLineEnd();
        editor.insert("\n");
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "addLineBefore",
      description: "Add new line before the current line",
      exec: function (editor) {
        editor.selection.clearSelection();
        var cursor = editor.getCursorPosition();
        editor.selection.moveTo(cursor.row - 1, Number.MAX_VALUE);
        editor.insert("\n");
        if (cursor.row === 0) editor.navigateUp();
      },
      multiSelectAction: "forEach",
      scrollIntoView: "cursor",
    },
    {
      name: "openCommandPallete",
      exec: function (editor) {
        console.warn(
          "This is an obsolete command. Please use `openCommandPalette` instead.",
        );
        editor.prompt({ $type: "commands" });
      },
      readOnly: true,
    },
    {
      name: "openCommandPalette",
      description: "Open command palette",
      bindKey: bindKey("F1", "F1"),
      exec: function (editor) {
        editor.prompt({ $type: "commands" });
      },
      readOnly: true,
    },
    {
      name: "modeSelect",
      description: "Change language mode...",
      bindKey: bindKey(null, null),
      exec: function (editor) {
        editor.prompt({ $type: "modes" });
      },
      readOnly: true,
    },
  ];
  for (var i = 1; i < 9; i++) {
    exports.commands.push({
      name: "foldToLevel" + i,
      description: "Fold To Level " + i,
      level: i,
      exec: function (editor) {
        editor.session.foldToLevel(this.level);
      },
      scrollIntoView: "center",
      readOnly: true,
    });
  }
});

define("ace/line_widgets", [
  "require",
  "exports",
  "module",
  "ace/lib/dom",
], function (require, exports, module) {
  "use strict";
  var dom = require("./lib/dom");
  var LineWidgets = /** @class */ (function () {
    function LineWidgets(session) {
      this.session = session;
      this.session.widgetManager = this;
      this.session.getRowLength = this.getRowLength;
      this.session.$getWidgetScreenLength = this.$getWidgetScreenLength;
      this.updateOnChange = this.updateOnChange.bind(this);
      this.renderWidgets = this.renderWidgets.bind(this);
      this.measureWidgets = this.measureWidgets.bind(this);
      this.session._changedWidgets = [];
      this.$onChangeEditor = this.$onChangeEditor.bind(this);
      this.session.on("change", this.updateOnChange);
      this.session.on("changeFold", this.updateOnFold);
      this.session.on("changeEditor", this.$onChangeEditor);
    }
    LineWidgets.prototype.getRowLength = function (row) {
      var h;
      if (this.lineWidgets)
        h = (this.lineWidgets[row] && this.lineWidgets[row].rowCount) || 0;
      else h = 0;
      if (!this["$useWrapMode"] || !this["$wrapData"][row]) {
        return 1 + h;
      } else {
        return this["$wrapData"][row].length + 1 + h;
      }
    };
    LineWidgets.prototype.$getWidgetScreenLength = function () {
      var screenRows = 0;
      this.lineWidgets.forEach(function (w) {
        if (w && w.rowCount && !w.hidden) screenRows += w.rowCount;
      });
      return screenRows;
    };
    LineWidgets.prototype.$onChangeEditor = function (e) {
      this.attach(e.editor);
    };
    LineWidgets.prototype.attach = function (editor) {
      if (editor && editor.widgetManager && editor.widgetManager != this)
        editor.widgetManager.detach();
      if (this.editor == editor) return;
      this.detach();
      this.editor = editor;
      if (editor) {
        editor.widgetManager = this;
        editor.renderer.on("beforeRender", this.measureWidgets);
        editor.renderer.on("afterRender", this.renderWidgets);
      }
    };
    LineWidgets.prototype.detach = function (e) {
      var editor = this.editor;
      if (!editor) return;
      this.editor = null;
      editor.widgetManager = null;
      editor.renderer.off("beforeRender", this.measureWidgets);
      editor.renderer.off("afterRender", this.renderWidgets);
      var lineWidgets = this.session.lineWidgets;
      lineWidgets &&
        lineWidgets.forEach(function (w) {
          if (w && w.el && w.el.parentNode) {
            w._inDocument = false;
            w.el.parentNode.removeChild(w.el);
          }
        });
    };
    LineWidgets.prototype.updateOnFold = function (e, session) {
      var lineWidgets = session.lineWidgets;
      if (!lineWidgets || !e.action) return;
      var fold = e.data;
      var start = fold.start.row;
      var end = fold.end.row;
      var hide = e.action == "add";
      for (var i = start + 1; i < end; i++) {
        if (lineWidgets[i]) lineWidgets[i].hidden = hide;
      }
      if (lineWidgets[end]) {
        if (hide) {
          if (!lineWidgets[start]) lineWidgets[start] = lineWidgets[end];
          else lineWidgets[end].hidden = hide;
        } else {
          if (lineWidgets[start] == lineWidgets[end])
            lineWidgets[start] = undefined;
          lineWidgets[end].hidden = hide;
        }
      }
    };
    LineWidgets.prototype.updateOnChange = function (delta) {
      var lineWidgets = this.session.lineWidgets;
      if (!lineWidgets) return;
      var startRow = delta.start.row;
      var len = delta.end.row - startRow;
      if (len === 0) {
      } else if (delta.action == "remove") {
        var removed = lineWidgets.splice(startRow + 1, len);
        if (!lineWidgets[startRow] && removed[removed.length - 1]) {
          lineWidgets[startRow] = removed.pop();
        }
        removed.forEach(function (w) {
          w && this.removeLineWidget(w);
        }, this);
        this.$updateRows();
      } else {
        var args = new Array(len);
        if (lineWidgets[startRow] && lineWidgets[startRow].column != null) {
          if (delta.start.column > lineWidgets[startRow].column) startRow++;
        }
        args.unshift(startRow, 0);
        lineWidgets.splice.apply(lineWidgets, args);
        this.$updateRows();
      }
    };
    LineWidgets.prototype.$updateRows = function () {
      var lineWidgets = this.session.lineWidgets;
      if (!lineWidgets) return;
      var noWidgets = true;
      lineWidgets.forEach(function (w, i) {
        if (w) {
          noWidgets = false;
          w.row = i;
          while (w.$oldWidget) {
            w.$oldWidget.row = i;
            w = w.$oldWidget;
          }
        }
      });
      if (noWidgets) this.session.lineWidgets = null;
    };
    LineWidgets.prototype.$registerLineWidget = function (w) {
      if (!this.session.lineWidgets)
        this.session.lineWidgets = new Array(this.session.getLength());
      var old = this.session.lineWidgets[w.row];
      if (old) {
        w.$oldWidget = old;
        if (old.el && old.el.parentNode) {
          old.el.parentNode.removeChild(old.el);
          old._inDocument = false;
        }
      }
      this.session.lineWidgets[w.row] = w;
      return w;
    };
    LineWidgets.prototype.addLineWidget = function (w) {
      this.$registerLineWidget(w);
      w.session = this.session;
      if (!this.editor) return w;
      var renderer = this.editor.renderer;
      if (w.html && !w.el) {
        w.el = dom.createElement("div");
        w.el.innerHTML = w.html;
      }
      if (w.text && !w.el) {
        w.el = dom.createElement("div");
        w.el.textContent = w.text;
      }
      if (w.el) {
        dom.addCssClass(w.el, "ace_lineWidgetContainer");
        if (w.className) {
          dom.addCssClass(w.el, w.className);
        }
        w.el.style.position = "absolute";
        w.el.style.zIndex = "5";
        renderer.container.appendChild(w.el);
        w._inDocument = true;
        if (!w.coverGutter) {
          w.el.style.zIndex = "3";
        }
        if (w.pixelHeight == null) {
          w.pixelHeight = w.el.offsetHeight;
        }
      }
      if (w.rowCount == null) {
        w.rowCount = w.pixelHeight / renderer.layerConfig.lineHeight;
      }
      var fold = this.session.getFoldAt(w.row, 0);
      w.$fold = fold;
      if (fold) {
        var lineWidgets = this.session.lineWidgets;
        if (w.row == fold.end.row && !lineWidgets[fold.start.row])
          lineWidgets[fold.start.row] = w;
        else w.hidden = true;
      }
      this.session._emit("changeFold", { data: { start: { row: w.row } } });
      this.$updateRows();
      this.renderWidgets(null, renderer);
      this.onWidgetChanged(w);
      return w;
    };
    LineWidgets.prototype.removeLineWidget = function (w) {
      w._inDocument = false;
      w.session = null;
      if (w.el && w.el.parentNode) w.el.parentNode.removeChild(w.el);
      if (w.editor && w.editor.destroy)
        try {
          w.editor.destroy();
        } catch (e) {}
      if (this.session.lineWidgets) {
        var w1 = this.session.lineWidgets[w.row];
        if (w1 == w) {
          this.session.lineWidgets[w.row] = w.$oldWidget;
          if (w.$oldWidget) this.onWidgetChanged(w.$oldWidget);
        } else {
          while (w1) {
            if (w1.$oldWidget == w) {
              w1.$oldWidget = w.$oldWidget;
              break;
            }
            w1 = w1.$oldWidget;
          }
        }
      }
      this.session._emit("changeFold", { data: { start: { row: w.row } } });
      this.$updateRows();
    };
    LineWidgets.prototype.getWidgetsAtRow = function (row) {
      var lineWidgets = this.session.lineWidgets;
      var w = lineWidgets && lineWidgets[row];
      var list = [];
      while (w) {
        list.push(w);
        w = w.$oldWidget;
      }
      return list;
    };
    LineWidgets.prototype.onWidgetChanged = function (w) {
      this.session._changedWidgets.push(w);
      this.editor && this.editor.renderer.updateFull();
    };
    LineWidgets.prototype.measureWidgets = function (e, renderer) {
      var changedWidgets = this.session._changedWidgets;
      var config = renderer.layerConfig;
      if (!changedWidgets || !changedWidgets.length) return;
      var min = Infinity;
      for (var i = 0; i < changedWidgets.length; i++) {
        var w = changedWidgets[i];
        if (!w || !w.el) continue;
        if (w.session != this.session) continue;
        if (!w._inDocument) {
          if (this.session.lineWidgets[w.row] != w) continue;
          w._inDocument = true;
          renderer.container.appendChild(w.el);
        }
        w.h = w.el.offsetHeight;
        if (!w.fixedWidth) {
          w.w = w.el.offsetWidth;
          w.screenWidth = Math.ceil(w.w / config.characterWidth);
        }
        var rowCount = w.h / config.lineHeight;
        if (w.coverLine) {
          rowCount -= this.session.getRowLineCount(w.row);
          if (rowCount < 0) rowCount = 0;
        }
        if (w.rowCount != rowCount) {
          w.rowCount = rowCount;
          if (w.row < min) min = w.row;
        }
      }
      if (min != Infinity) {
        this.session._emit("changeFold", { data: { start: { row: min } } });
        this.session.lineWidgetWidth = null;
      }
      this.session._changedWidgets = [];
    };
    LineWidgets.prototype.renderWidgets = function (e, renderer) {
      var config = renderer.layerConfig;
      var lineWidgets = this.session.lineWidgets;
      if (!lineWidgets) return;
      var first = Math.min(this.firstRow, config.firstRow);
      var last = Math.max(this.lastRow, config.lastRow, lineWidgets.length);
      while (first > 0 && !lineWidgets[first]) first--;
      this.firstRow = config.firstRow;
      this.lastRow = config.lastRow;
      renderer.$cursorLayer.config = config;
      for (var i = first; i <= last; i++) {
        var w = lineWidgets[i];
        if (!w || !w.el) continue;
        if (w.hidden) {
          w.el.style.top = -100 - (w.pixelHeight || 0) + "px";
          continue;
        }
        if (!w._inDocument) {
          w._inDocument = true;
          renderer.container.appendChild(w.el);
        }
        var top = renderer.$cursorLayer.getPixelPosition(
          { row: i, column: 0 },
          true,
        ).top;
        if (!w.coverLine)
          top += config.lineHeight * this.session.getRowLineCount(w.row);
        w.el.style.top = top - config.offset + "px";
        var left = w.coverGutter ? 0 : renderer.gutterWidth;
        if (!w.fixedWidth) left -= renderer.scrollLeft;
        w.el.style.left = left + "px";
        if (w.fullWidth && w.screenWidth) {
          w.el.style.minWidth = config.width + 2 * config.padding + "px";
        }
        if (w.fixedWidth) {
          w.el.style.right = renderer.scrollBar.getWidth() + "px";
        } else {
          w.el.style.right = "";
        }
      }
    };
    return LineWidgets;
  })();
  exports.LineWidgets = LineWidgets;
});

define("ace/keyboard/gutter_handler", [
  "require",
  "exports",
  "module",
  "ace/lib/keys",
  "ace/mouse/default_gutter_handler",
], function (require, exports, module) {
  "use strict";
  var keys = require("../lib/keys");
  var GutterTooltip = require("../mouse/default_gutter_handler").GutterTooltip;
  var GutterKeyboardHandler = /** @class */ (function () {
    function GutterKeyboardHandler(editor) {
      this.editor = editor;
      this.gutterLayer = editor.renderer.$gutterLayer;
      this.element = editor.renderer.$gutter;
      this.lines = editor.renderer.$gutterLayer.$lines;
      this.activeRowIndex = null;
      this.activeLane = null;
      this.annotationTooltip = new GutterTooltip(this.editor);
    }
    GutterKeyboardHandler.prototype.addListener = function () {
      this.element.addEventListener(
        "keydown",
        this.$onGutterKeyDown.bind(this),
      );
      this.element.addEventListener("focusout", this.$blurGutter.bind(this));
      this.editor.on("mousewheel", this.$blurGutter.bind(this));
    };
    GutterKeyboardHandler.prototype.removeListener = function () {
      this.element.removeEventListener(
        "keydown",
        this.$onGutterKeyDown.bind(this),
      );
      this.element.removeEventListener("focusout", this.$blurGutter.bind(this));
      this.editor.off("mousewheel", this.$blurGutter.bind(this));
    };
    GutterKeyboardHandler.prototype.$onGutterKeyDown = function (e) {
      if (this.annotationTooltip.isOpen) {
        e.preventDefault();
        if (e.keyCode === keys["escape"]) this.annotationTooltip.hideTooltip();
        return;
      }
      if (e.target === this.element) {
        if (e.keyCode != keys["enter"]) {
          return;
        }
        e.preventDefault();
        var row = this.editor.getCursorPosition().row;
        if (!this.editor.isRowVisible(row))
          this.editor.scrollToLine(row, true, true);
        setTimeout(
          function () {
            var index = this.$rowToRowIndex(this.gutterLayer.$cursorCell.row);
            var nearestFoldIndex = this.$findNearestFoldWidget(index);
            var nearestAnnotationIndex = this.$findNearestAnnotation(index);
            if (nearestFoldIndex === null && nearestAnnotationIndex === null)
              return;
            if (nearestFoldIndex === null && nearestAnnotationIndex !== null) {
              this.activeRowIndex = nearestAnnotationIndex;
              this.activeLane = "annotation";
              this.$focusAnnotation(this.activeRowIndex);
              return;
            }
            if (nearestFoldIndex !== null && nearestAnnotationIndex === null) {
              this.activeRowIndex = nearestFoldIndex;
              this.activeLane = "fold";
              this.$focusFoldWidget(this.activeRowIndex);
              return;
            }
            if (
              Math.abs(nearestAnnotationIndex - index) <
              Math.abs(nearestFoldIndex - index)
            ) {
              this.activeRowIndex = nearestAnnotationIndex;
              this.activeLane = "annotation";
              this.$focusAnnotation(this.activeRowIndex);
              return;
            } else {
              this.activeRowIndex = nearestFoldIndex;
              this.activeLane = "fold";
              this.$focusFoldWidget(this.activeRowIndex);
              return;
            }
          }.bind(this),
          10,
        );
        return;
      }
      this.$handleGutterKeyboardInteraction(e);
      setTimeout(
        function () {
          this.editor._signal(
            "gutterkeydown",
            new GutterKeyboardEvent(e, this),
          );
        }.bind(this),
        10,
      );
    };
    GutterKeyboardHandler.prototype.$handleGutterKeyboardInteraction =
      function (e) {
        if (e.keyCode === keys["tab"]) {
          e.preventDefault();
          return;
        }
        if (e.keyCode === keys["escape"]) {
          e.preventDefault();
          this.$blurGutter();
          this.element.focus();
          this.lane = null;
          return;
        }
        if (e.keyCode === keys["up"]) {
          e.preventDefault();
          switch (this.activeLane) {
            case "fold":
              this.$moveFoldWidgetUp();
              break;
            case "annotation":
              this.$moveAnnotationUp();
              break;
          }
          return;
        }
        if (e.keyCode === keys["down"]) {
          e.preventDefault();
          switch (this.activeLane) {
            case "fold":
              this.$moveFoldWidgetDown();
              break;
            case "annotation":
              this.$moveAnnotationDown();
              break;
          }
          return;
        }
        if (e.keyCode === keys["left"]) {
          e.preventDefault();
          this.$switchLane("annotation");
          return;
        }
        if (e.keyCode === keys["right"]) {
          e.preventDefault();
          this.$switchLane("fold");
          return;
        }
        if (e.keyCode === keys["enter"] || e.keyCode === keys["space"]) {
          e.preventDefault();
          switch (this.activeLane) {
            case "fold":
              if (
                this.gutterLayer.session.foldWidgets[
                  this.$rowIndexToRow(this.activeRowIndex)
                ] === "start"
              ) {
                var rowFoldingWidget = this.$rowIndexToRow(this.activeRowIndex);
                this.editor.session.onFoldWidgetClick(
                  this.$rowIndexToRow(this.activeRowIndex),
                  e,
                );
                setTimeout(
                  function () {
                    if (
                      this.$rowIndexToRow(this.activeRowIndex) !==
                      rowFoldingWidget
                    ) {
                      this.$blurFoldWidget(this.activeRowIndex);
                      this.activeRowIndex =
                        this.$rowToRowIndex(rowFoldingWidget);
                      this.$focusFoldWidget(this.activeRowIndex);
                    }
                  }.bind(this),
                  10,
                );
                break;
              } else if (
                this.gutterLayer.session.foldWidgets[
                  this.$rowIndexToRow(this.activeRowIndex)
                ] === "end"
              ) {
                break;
              }
              return;
            case "annotation":
              var gutterElement =
                this.lines.cells[this.activeRowIndex].element.childNodes[2];
              var rect = gutterElement.getBoundingClientRect();
              var style = this.annotationTooltip.getElement().style;
              style.left = rect.right + "px";
              style.top = rect.bottom + "px";
              this.annotationTooltip.showTooltip(
                this.$rowIndexToRow(this.activeRowIndex),
              );
              break;
          }
          return;
        }
      };
    GutterKeyboardHandler.prototype.$blurGutter = function () {
      if (this.activeRowIndex !== null) {
        switch (this.activeLane) {
          case "fold":
            this.$blurFoldWidget(this.activeRowIndex);
            break;
          case "annotation":
            this.$blurAnnotation(this.activeRowIndex);
            break;
        }
      }
      if (this.annotationTooltip.isOpen) this.annotationTooltip.hideTooltip();
      return;
    };
    GutterKeyboardHandler.prototype.$isFoldWidgetVisible = function (index) {
      var isRowFullyVisible = this.editor.isRowFullyVisible(
        this.$rowIndexToRow(index),
      );
      var isIconVisible = this.$getFoldWidget(index).style.display !== "none";
      return isRowFullyVisible && isIconVisible;
    };
    GutterKeyboardHandler.prototype.$isAnnotationVisible = function (index) {
      var isRowFullyVisible = this.editor.isRowFullyVisible(
        this.$rowIndexToRow(index),
      );
      var isIconVisible = this.$getAnnotation(index).style.display !== "none";
      return isRowFullyVisible && isIconVisible;
    };
    GutterKeyboardHandler.prototype.$getFoldWidget = function (index) {
      var cell = this.lines.get(index);
      var element = cell.element;
      return element.childNodes[1];
    };
    GutterKeyboardHandler.prototype.$getAnnotation = function (index) {
      var cell = this.lines.get(index);
      var element = cell.element;
      return element.childNodes[2];
    };
    GutterKeyboardHandler.prototype.$findNearestFoldWidget = function (index) {
      if (this.$isFoldWidgetVisible(index)) return index;
      var i = 0;
      while (index - i > 0 || index + i < this.lines.getLength() - 1) {
        i++;
        if (index - i >= 0 && this.$isFoldWidgetVisible(index - i))
          return index - i;
        if (
          index + i <= this.lines.getLength() - 1 &&
          this.$isFoldWidgetVisible(index + i)
        )
          return index + i;
      }
      return null;
    };
    GutterKeyboardHandler.prototype.$findNearestAnnotation = function (index) {
      if (this.$isAnnotationVisible(index)) return index;
      var i = 0;
      while (index - i > 0 || index + i < this.lines.getLength() - 1) {
        i++;
        if (index - i >= 0 && this.$isAnnotationVisible(index - i))
          return index - i;
        if (
          index + i <= this.lines.getLength() - 1 &&
          this.$isAnnotationVisible(index + i)
        )
          return index + i;
      }
      return null;
    };
    GutterKeyboardHandler.prototype.$focusFoldWidget = function (index) {
      if (index == null) return;
      var foldWidget = this.$getFoldWidget(index);
      foldWidget.classList.add(this.editor.renderer.keyboardFocusClassName);
      foldWidget.focus();
    };
    GutterKeyboardHandler.prototype.$focusAnnotation = function (index) {
      if (index == null) return;
      var annotation = this.$getAnnotation(index);
      annotation.classList.add(this.editor.renderer.keyboardFocusClassName);
      annotation.focus();
    };
    GutterKeyboardHandler.prototype.$blurFoldWidget = function (index) {
      var foldWidget = this.$getFoldWidget(index);
      foldWidget.classList.remove(this.editor.renderer.keyboardFocusClassName);
      foldWidget.blur();
    };
    GutterKeyboardHandler.prototype.$blurAnnotation = function (index) {
      var annotation = this.$getAnnotation(index);
      annotation.classList.remove(this.editor.renderer.keyboardFocusClassName);
      annotation.blur();
    };
    GutterKeyboardHandler.prototype.$moveFoldWidgetUp = function () {
      var index = this.activeRowIndex;
      while (index > 0) {
        index--;
        if (this.$isFoldWidgetVisible(index)) {
          this.$blurFoldWidget(this.activeRowIndex);
          this.activeRowIndex = index;
          this.$focusFoldWidget(this.activeRowIndex);
          return;
        }
      }
      return;
    };
    GutterKeyboardHandler.prototype.$moveFoldWidgetDown = function () {
      var index = this.activeRowIndex;
      while (index < this.lines.getLength() - 1) {
        index++;
        if (this.$isFoldWidgetVisible(index)) {
          this.$blurFoldWidget(this.activeRowIndex);
          this.activeRowIndex = index;
          this.$focusFoldWidget(this.activeRowIndex);
          return;
        }
      }
      return;
    };
    GutterKeyboardHandler.prototype.$moveAnnotationUp = function () {
      var index = this.activeRowIndex;
      while (index > 0) {
        index--;
        if (this.$isAnnotationVisible(index)) {
          this.$blurAnnotation(this.activeRowIndex);
          this.activeRowIndex = index;
          this.$focusAnnotation(this.activeRowIndex);
          return;
        }
      }
      return;
    };
    GutterKeyboardHandler.prototype.$moveAnnotationDown = function () {
      var index = this.activeRowIndex;
      while (index < this.lines.getLength() - 1) {
        index++;
        if (this.$isAnnotationVisible(index)) {
          this.$blurAnnotation(this.activeRowIndex);
          this.activeRowIndex = index;
          this.$focusAnnotation(this.activeRowIndex);
          return;
        }
      }
      return;
    };
    GutterKeyboardHandler.prototype.$switchLane = function (desinationLane) {
      switch (desinationLane) {
        case "annotation":
          if (this.activeLane === "annotation") {
            break;
          }
          var annotationIndex = this.$findNearestAnnotation(
            this.activeRowIndex,
          );
          if (annotationIndex == null) {
            break;
          }
          this.activeLane = "annotation";
          this.$blurFoldWidget(this.activeRowIndex);
          this.activeRowIndex = annotationIndex;
          this.$focusAnnotation(this.activeRowIndex);
          break;
        case "fold":
          if (this.activeLane === "fold") {
            break;
          }
          var foldWidgetIndex = this.$findNearestFoldWidget(
            this.activeRowIndex,
          );
          if (foldWidgetIndex == null) {
            break;
          }
          this.activeLane = "fold";
          this.$blurAnnotation(this.activeRowIndex);
          this.activeRowIndex = foldWidgetIndex;
          this.$focusFoldWidget(this.activeRowIndex);
          break;
      }
      return;
    };
    GutterKeyboardHandler.prototype.$rowIndexToRow = function (index) {
      var cell = this.lines.get(index);
      if (cell) return cell.row;
      return null;
    };
    GutterKeyboardHandler.prototype.$rowToRowIndex = function (row) {
      for (var i = 0; i < this.lines.getLength(); i++) {
        var cell = this.lines.get(i);
        if (cell.row == row) return i;
      }
      return null;
    };
    return GutterKeyboardHandler;
  })();
  exports.GutterKeyboardHandler = GutterKeyboardHandler;
  var GutterKeyboardEvent = /** @class */ (function () {
    function GutterKeyboardEvent(domEvent, gutterKeyboardHandler) {
      this.gutterKeyboardHandler = gutterKeyboardHandler;
      this.domEvent = domEvent;
    }
    GutterKeyboardEvent.prototype.getKey = function () {
      return keys.keyCodeToString(this.domEvent.keyCode);
    };
    GutterKeyboardEvent.prototype.getRow = function () {
      return this.gutterKeyboardHandler.$rowIndexToRow(
        this.gutterKeyboardHandler.activeRowIndex,
      );
    };
    GutterKeyboardEvent.prototype.isInAnnotationLane = function () {
      return this.gutterKeyboardHandler.activeLane === "annotation";
    };
    GutterKeyboardEvent.prototype.isInFoldLane = function () {
      return this.gutterKeyboardHandler.activeLane === "fold";
    };
    return GutterKeyboardEvent;
  })();
  exports.GutterKeyboardEvent = GutterKeyboardEvent;
});

define("ace/editor", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/dom",
  "ace/lib/lang",
  "ace/lib/useragent",
  "ace/keyboard/textinput",
  "ace/mouse/mouse_handler",
  "ace/mouse/fold_handler",
  "ace/keyboard/keybinding",
  "ace/edit_session",
  "ace/search",
  "ace/range",
  "ace/lib/event_emitter",
  "ace/commands/command_manager",
  "ace/commands/default_commands",
  "ace/config",
  "ace/token_iterator",
  "ace/line_widgets",
  "ace/keyboard/gutter_handler",
  "ace/config",
  "ace/clipboard",
  "ace/lib/keys",
], function (require, exports, module) {
  "use strict";
  var __values =
    (this && this.__values) ||
    function (o) {
      var s = typeof Symbol === "function" && Symbol.iterator,
        m = s && o[s],
        i = 0;
      if (m) return m.call(o);
      if (o && typeof o.length === "number")
        return {
          next: function () {
            if (o && i >= o.length) o = void 0;
            return { value: o && o[i++], done: !o };
          },
        };
      throw new TypeError(
        s ? "Object is not iterable." : "Symbol.iterator is not defined.",
      );
    };
  var oop = require("./lib/oop");
  var dom = require("./lib/dom");
  var lang = require("./lib/lang");
  var useragent = require("./lib/useragent");
  var TextInput = require("./keyboard/textinput").TextInput;
  var MouseHandler = require("./mouse/mouse_handler").MouseHandler;
  var FoldHandler = require("./mouse/fold_handler").FoldHandler;
  var KeyBinding = require("./keyboard/keybinding").KeyBinding;
  var EditSession = require("./edit_session").EditSession;
  var Search = require("./search").Search;
  var Range = require("./range").Range;
  var EventEmitter = require("./lib/event_emitter").EventEmitter;
  var CommandManager = require("./commands/command_manager").CommandManager;
  var defaultCommands = require("./commands/default_commands").commands;
  var config = require("./config");
  var TokenIterator = require("./token_iterator").TokenIterator;
  var LineWidgets = require("./line_widgets").LineWidgets;
  var GutterKeyboardHandler =
    require("./keyboard/gutter_handler").GutterKeyboardHandler;
  var nls = require("./config").nls;
  var clipboard = require("./clipboard");
  var keys = require("./lib/keys");
  var Editor = /** @class */ (function () {
    function Editor(renderer, session, options) {
      this.session;
      this.$toDestroy = [];
      var container = renderer.getContainerElement();
      this.container = container;
      this.renderer = renderer;
      this.id = "editor" + ++Editor.$uid;
      this.commands = new CommandManager(
        useragent.isMac ? "mac" : "win",
        defaultCommands,
      );
      if (typeof document == "object") {
        this.textInput = new TextInput(renderer.getTextAreaContainer(), this);
        this.renderer.textarea = this.textInput.getElement();
        this.$mouseHandler = new MouseHandler(this);
        new FoldHandler(this);
      }
      this.keyBinding = new KeyBinding(this);
      this.$search = new Search().set({
        wrap: true,
      });
      this.$historyTracker = this.$historyTracker.bind(this);
      this.commands.on("exec", this.$historyTracker);
      this.$initOperationListeners();
      this._$emitInputEvent = lang.delayedCall(
        function () {
          this._signal("input", {});
          if (this.session && !this.session.destroyed)
            this.session.bgTokenizer.scheduleStart();
        }.bind(this),
      );
      this.on("change", function (_, _self) {
        _self._$emitInputEvent.schedule(31);
      });
      this.setSession(
        session || (options && options.session) || new EditSession(""),
      );
      config.resetOptions(this);
      if (options) this.setOptions(options);
      config._signal("editor", this);
    }
    Editor.prototype.$initOperationListeners = function () {
      this.commands.on("exec", this.startOperation.bind(this), true);
      this.commands.on("afterExec", this.endOperation.bind(this), true);
      this.$opResetTimer = lang.delayedCall(this.endOperation.bind(this, true));
      this.on(
        "change",
        function () {
          if (!this.curOp) {
            this.startOperation();
            this.curOp.selectionBefore = this.$lastSel;
          }
          this.curOp.docChanged = true;
        }.bind(this),
        true,
      );
      this.on(
        "changeSelection",
        function () {
          if (!this.curOp) {
            this.startOperation();
            this.curOp.selectionBefore = this.$lastSel;
          }
          this.curOp.selectionChanged = true;
        }.bind(this),
        true,
      );
    };
    Editor.prototype.startOperation = function (commandEvent) {
      if (this.curOp) {
        if (!commandEvent || this.curOp.command) return;
        this.prevOp = this.curOp;
      }
      if (!commandEvent) {
        this.previousCommand = null;
        commandEvent = {};
      }
      this.$opResetTimer.schedule();
      this.curOp = this.session.curOp = {
        command: commandEvent.command || {},
        args: commandEvent.args,
        scrollTop: this.renderer.scrollTop,
      };
      this.curOp.selectionBefore = this.selection.toJSON();
    };
    Editor.prototype.endOperation = function (e) {
      if (this.curOp && this.session) {
        if ((e && e.returnValue === false) || !this.session)
          return (this.curOp = null);
        if (
          e == true &&
          this.curOp.command &&
          this.curOp.command.name == "mouse"
        )
          return;
        this._signal("beforeEndOperation");
        if (!this.curOp) return;
        var command = this.curOp.command;
        var scrollIntoView = command && command.scrollIntoView;
        if (scrollIntoView) {
          switch (scrollIntoView) {
            case "center-animate":
              scrollIntoView = "animate";
            case "center":
              this.renderer.scrollCursorIntoView(null, 0.5);
              break;
            case "animate":
            case "cursor":
              this.renderer.scrollCursorIntoView();
              break;
            case "selectionPart":
              var range = this.selection.getRange();
              var config = this.renderer.layerConfig;
              if (
                range.start.row >= config.lastRow ||
                range.end.row <= config.firstRow
              ) {
                this.renderer.scrollSelectionIntoView(
                  this.selection.anchor,
                  this.selection.lead,
                );
              }
              break;
            default:
              break;
          }
          if (scrollIntoView == "animate")
            this.renderer.animateScrolling(this.curOp.scrollTop);
        }
        var sel = this.selection.toJSON();
        this.curOp.selectionAfter = sel;
        this.$lastSel = this.selection.toJSON();
        this.session.getUndoManager().addSelection(sel);
        this.prevOp = this.curOp;
        this.curOp = null;
      }
    };
    Editor.prototype.$historyTracker = function (e) {
      if (!this.$mergeUndoDeltas) return;
      var prev = this.prevOp;
      var mergeableCommands = this.$mergeableCommands;
      var shouldMerge = prev.command && e.command.name == prev.command.name;
      if (e.command.name == "insertstring") {
        var text = e.args;
        if (this.mergeNextCommand === undefined) this.mergeNextCommand = true;
        shouldMerge =
          shouldMerge &&
          this.mergeNextCommand && // previous command allows to coalesce with
          (!/\s/.test(text) || /\s/.test(prev.args)); // previous insertion was of same type
        this.mergeNextCommand = true;
      } else {
        shouldMerge =
          shouldMerge && mergeableCommands.indexOf(e.command.name) !== -1; // the command is mergeable
      }
      if (
        this.$mergeUndoDeltas != "always" &&
        Date.now() - this.sequenceStartTime > 2000
      ) {
        shouldMerge = false; // the sequence is too long
      }
      if (shouldMerge) this.session.mergeUndoDeltas = true;
      else if (mergeableCommands.indexOf(e.command.name) !== -1)
        this.sequenceStartTime = Date.now();
    };
    Editor.prototype.setKeyboardHandler = function (keyboardHandler, cb) {
      if (
        keyboardHandler &&
        typeof keyboardHandler === "string" &&
        keyboardHandler != "ace"
      ) {
        this.$keybindingId = keyboardHandler;
        var _self = this;
        config.loadModule(["keybinding", keyboardHandler], function (module) {
          if (_self.$keybindingId == keyboardHandler)
            _self.keyBinding.setKeyboardHandler(module && module.handler);
          cb && cb();
        });
      } else {
        this.$keybindingId = null;
        this.keyBinding.setKeyboardHandler(keyboardHandler);
        cb && cb();
      }
    };
    Editor.prototype.getKeyboardHandler = function () {
      return this.keyBinding.getKeyboardHandler();
    };
    Editor.prototype.setSession = function (session) {
      if (this.session == session) return;
      if (this.curOp) this.endOperation();
      this.curOp = {};
      var oldSession = this.session;
      if (oldSession) {
        this.session.off("change", this.$onDocumentChange);
        this.session.off("changeMode", this.$onChangeMode);
        this.session.off("tokenizerUpdate", this.$onTokenizerUpdate);
        this.session.off("changeTabSize", this.$onChangeTabSize);
        this.session.off("changeWrapLimit", this.$onChangeWrapLimit);
        this.session.off("changeWrapMode", this.$onChangeWrapMode);
        this.session.off("changeFold", this.$onChangeFold);
        this.session.off("changeFrontMarker", this.$onChangeFrontMarker);
        this.session.off("changeBackMarker", this.$onChangeBackMarker);
        this.session.off("changeBreakpoint", this.$onChangeBreakpoint);
        this.session.off("changeAnnotation", this.$onChangeAnnotation);
        this.session.off("changeOverwrite", this.$onCursorChange);
        this.session.off("changeScrollTop", this.$onScrollTopChange);
        this.session.off("changeScrollLeft", this.$onScrollLeftChange);
        var selection = this.session.getSelection();
        selection.off("changeCursor", this.$onCursorChange);
        selection.off("changeSelection", this.$onSelectionChange);
      }
      this.session = session;
      if (session) {
        this.$onDocumentChange = this.onDocumentChange.bind(this);
        session.on("change", this.$onDocumentChange);
        this.renderer.setSession(session);
        this.$onChangeMode = this.onChangeMode.bind(this);
        session.on("changeMode", this.$onChangeMode);
        this.$onTokenizerUpdate = this.onTokenizerUpdate.bind(this);
        session.on("tokenizerUpdate", this.$onTokenizerUpdate);
        this.$onChangeTabSize = this.renderer.onChangeTabSize.bind(
          this.renderer,
        );
        session.on("changeTabSize", this.$onChangeTabSize);
        this.$onChangeWrapLimit = this.onChangeWrapLimit.bind(this);
        session.on("changeWrapLimit", this.$onChangeWrapLimit);
        this.$onChangeWrapMode = this.onChangeWrapMode.bind(this);
        session.on("changeWrapMode", this.$onChangeWrapMode);
        this.$onChangeFold = this.onChangeFold.bind(this);
        session.on("changeFold", this.$onChangeFold);
        this.$onChangeFrontMarker = this.onChangeFrontMarker.bind(this);
        this.session.on("changeFrontMarker", this.$onChangeFrontMarker);
        this.$onChangeBackMarker = this.onChangeBackMarker.bind(this);
        this.session.on("changeBackMarker", this.$onChangeBackMarker);
        this.$onChangeBreakpoint = this.onChangeBreakpoint.bind(this);
        this.session.on("changeBreakpoint", this.$onChangeBreakpoint);
        this.$onChangeAnnotation = this.onChangeAnnotation.bind(this);
        this.session.on("changeAnnotation", this.$onChangeAnnotation);
        this.$onCursorChange = this.onCursorChange.bind(this);
        this.session.on("changeOverwrite", this.$onCursorChange);
        this.$onScrollTopChange = this.onScrollTopChange.bind(this);
        this.session.on("changeScrollTop", this.$onScrollTopChange);
        this.$onScrollLeftChange = this.onScrollLeftChange.bind(this);
        this.session.on("changeScrollLeft", this.$onScrollLeftChange);
        this.selection = session.getSelection();
        this.selection.on("changeCursor", this.$onCursorChange);
        this.$onSelectionChange = this.onSelectionChange.bind(this);
        this.selection.on("changeSelection", this.$onSelectionChange);
        this.onChangeMode();
        this.onCursorChange();
        this.onScrollTopChange();
        this.onScrollLeftChange();
        this.onSelectionChange();
        this.onChangeFrontMarker();
        this.onChangeBackMarker();
        this.onChangeBreakpoint();
        this.onChangeAnnotation();
        this.session.getUseWrapMode() && this.renderer.adjustWrapLimit();
        this.renderer.updateFull();
      } else {
        this.selection = null;
        this.renderer.setSession(session);
      }
      this._signal("changeSession", {
        session: session,
        oldSession: oldSession,
      });
      this.curOp = null;
      oldSession && oldSession._signal("changeEditor", { oldEditor: this });
      session && session._signal("changeEditor", { editor: this });
      if (session && !session.destroyed) session.bgTokenizer.scheduleStart();
    };
    Editor.prototype.getSession = function () {
      return this.session;
    };
    Editor.prototype.setValue = function (val, cursorPos) {
      this.session.doc.setValue(val);
      if (!cursorPos) this.selectAll();
      else if (cursorPos == 1) this.navigateFileEnd();
      else if (cursorPos == -1) this.navigateFileStart();
      return val;
    };
    Editor.prototype.getValue = function () {
      return this.session.getValue();
    };
    Editor.prototype.getSelection = function () {
      return this.selection;
    };
    Editor.prototype.resize = function (force) {
      this.renderer.onResize(force);
    };
    Editor.prototype.setTheme = function (theme, cb) {
      this.renderer.setTheme(theme, cb);
    };
    Editor.prototype.getTheme = function () {
      return this.renderer.getTheme();
    };
    Editor.prototype.setStyle = function (style) {
      this.renderer.setStyle(style);
    };
    Editor.prototype.unsetStyle = function (style) {
      this.renderer.unsetStyle(style);
    };
    Editor.prototype.getFontSize = function () {
      return (
        this.getOption("fontSize") || dom.computedStyle(this.container).fontSize
      );
    };
    Editor.prototype.setFontSize = function (size) {
      this.setOption("fontSize", size);
    };
    Editor.prototype.$highlightBrackets = function () {
      if (this.$highlightPending) {
        return;
      }
      var self = this;
      this.$highlightPending = true;
      setTimeout(function () {
        self.$highlightPending = false;
        var session = self.session;
        if (!session || session.destroyed) return;
        if (session.$bracketHighlight) {
          session.$bracketHighlight.markerIds.forEach(function (id) {
            session.removeMarker(id);
          });
          session.$bracketHighlight = null;
        }
        var pos = self.getCursorPosition();
        var handler = self.getKeyboardHandler();
        var isBackwards =
          handler &&
          handler.$getDirectionForHighlight &&
          handler.$getDirectionForHighlight(self);
        var ranges = session.getMatchingBracketRanges(pos, isBackwards);
        if (!ranges) {
          var iterator = new TokenIterator(session, pos.row, pos.column);
          var token = iterator.getCurrentToken();
          if (token && /\b(?:tag-open|tag-name)/.test(token.type)) {
            var tagNamesRanges = session.getMatchingTags(pos);
            if (tagNamesRanges)
              ranges = [
                tagNamesRanges.openTagName,
                tagNamesRanges.closeTagName,
              ];
          }
        }
        if (!ranges && session.$mode.getMatching)
          ranges = session.$mode.getMatching(self.session);
        if (!ranges) {
          if (self.getHighlightIndentGuides())
            self.renderer.$textLayer.$highlightIndentGuide();
          return;
        }
        var markerType = "ace_bracket";
        if (!Array.isArray(ranges)) {
          ranges = [ranges];
        } else if (ranges.length == 1) {
          markerType = "ace_error_bracket";
        }
        if (ranges.length == 2) {
          if (Range.comparePoints(ranges[0].end, ranges[1].start) == 0)
            ranges = [Range.fromPoints(ranges[0].start, ranges[1].end)];
          else if (Range.comparePoints(ranges[0].start, ranges[1].end) == 0)
            ranges = [Range.fromPoints(ranges[1].start, ranges[0].end)];
        }
        session.$bracketHighlight = {
          ranges: ranges,
          markerIds: ranges.map(function (range) {
            return session.addMarker(range, markerType, "text");
          }),
        };
        if (self.getHighlightIndentGuides())
          self.renderer.$textLayer.$highlightIndentGuide();
      }, 50);
    };
    Editor.prototype.focus = function () {
      this.textInput.focus();
    };
    Editor.prototype.isFocused = function () {
      return this.textInput.isFocused();
    };
    Editor.prototype.blur = function () {
      this.textInput.blur();
    };
    Editor.prototype.onFocus = function (e) {
      if (this.$isFocused) return;
      this.$isFocused = true;
      this.renderer.showCursor();
      this.renderer.visualizeFocus();
      this._emit("focus", e);
    };
    Editor.prototype.onBlur = function (e) {
      if (!this.$isFocused) return;
      this.$isFocused = false;
      this.renderer.hideCursor();
      this.renderer.visualizeBlur();
      this._emit("blur", e);
    };
    Editor.prototype.$cursorChange = function () {
      this.renderer.updateCursor();
      this.$highlightBrackets();
      this.$updateHighlightActiveLine();
    };
    Editor.prototype.onDocumentChange = function (delta) {
      var wrap = this.session.$useWrapMode;
      var lastRow = delta.start.row == delta.end.row ? delta.end.row : Infinity;
      this.renderer.updateLines(delta.start.row, lastRow, wrap);
      this._signal("change", delta);
      this.$cursorChange();
    };
    Editor.prototype.onTokenizerUpdate = function (e) {
      var rows = e.data;
      this.renderer.updateLines(rows.first, rows.last);
    };
    Editor.prototype.onScrollTopChange = function () {
      this.renderer.scrollToY(this.session.getScrollTop());
    };
    Editor.prototype.onScrollLeftChange = function () {
      this.renderer.scrollToX(this.session.getScrollLeft());
    };
    Editor.prototype.onCursorChange = function () {
      this.$cursorChange();
      this._signal("changeSelection");
    };
    Editor.prototype.$updateHighlightActiveLine = function () {
      var session = this.getSession();
      var highlight;
      if (this.$highlightActiveLine) {
        if (this.$selectionStyle != "line" || !this.selection.isMultiLine())
          highlight = this.getCursorPosition();
        if (
          this.renderer.theme &&
          this.renderer.theme.$selectionColorConflict &&
          !this.selection.isEmpty()
        )
          highlight = false;
        if (
          this.renderer.$maxLines &&
          this.session.getLength() === 1 &&
          !(this.renderer.$minLines > 1)
        )
          highlight = false;
      }
      if (session.$highlightLineMarker && !highlight) {
        session.removeMarker(session.$highlightLineMarker.id);
        session.$highlightLineMarker = null;
      } else if (!session.$highlightLineMarker && highlight) {
        var range = new Range(
          highlight.row,
          highlight.column,
          highlight.row,
          Infinity,
        );
        range.id = session.addMarker(range, "ace_active-line", "screenLine");
        session.$highlightLineMarker = range;
      } else if (highlight) {
        session.$highlightLineMarker.start.row = highlight.row;
        session.$highlightLineMarker.end.row = highlight.row;
        session.$highlightLineMarker.start.column = highlight.column;
        session._signal("changeBackMarker");
      }
    };
    Editor.prototype.onSelectionChange = function (e) {
      var session = this.session;
      if (session.$selectionMarker) {
        session.removeMarker(session.$selectionMarker);
      }
      session.$selectionMarker = null;
      if (!this.selection.isEmpty()) {
        var range = this.selection.getRange();
        var style = this.getSelectionStyle();
        session.$selectionMarker = session.addMarker(
          range,
          "ace_selection",
          style,
        );
      } else {
        this.$updateHighlightActiveLine();
      }
      var re =
        this.$highlightSelectedWord && this.$getSelectionHighLightRegexp();
      this.session.highlight(re);
      this._signal("changeSelection");
    };
    Editor.prototype.$getSelectionHighLightRegexp = function () {
      var session = this.session;
      var selection = this.getSelectionRange();
      if (selection.isEmpty() || selection.isMultiLine()) return;
      var startColumn = selection.start.column;
      var endColumn = selection.end.column;
      var line = session.getLine(selection.start.row);
      var needle = line.substring(startColumn, endColumn);
      if (needle.length > 5000 || !/[\w\d]/.test(needle)) return;
      var re = this.$search.$assembleRegExp({
        wholeWord: true,
        caseSensitive: true,
        needle: needle,
      });
      var wordWithBoundary = line.substring(startColumn - 1, endColumn + 1);
      if (!re.test(wordWithBoundary)) return;
      return re;
    };
    Editor.prototype.onChangeFrontMarker = function () {
      this.renderer.updateFrontMarkers();
    };
    Editor.prototype.onChangeBackMarker = function () {
      this.renderer.updateBackMarkers();
    };
    Editor.prototype.onChangeBreakpoint = function () {
      this.renderer.updateBreakpoints();
    };
    Editor.prototype.onChangeAnnotation = function () {
      this.renderer.setAnnotations(this.session.getAnnotations());
    };
    Editor.prototype.onChangeMode = function (e) {
      this.renderer.updateText();
      this._emit("changeMode", e);
    };
    Editor.prototype.onChangeWrapLimit = function () {
      this.renderer.updateFull();
    };
    Editor.prototype.onChangeWrapMode = function () {
      this.renderer.onResize(true);
    };
    Editor.prototype.onChangeFold = function () {
      this.$updateHighlightActiveLine();
      this.renderer.updateFull();
    };
    Editor.prototype.getSelectedText = function () {
      return this.session.getTextRange(this.getSelectionRange());
    };
    Editor.prototype.getCopyText = function () {
      var text = this.getSelectedText();
      var nl = this.session.doc.getNewLineCharacter();
      var copyLine = false;
      if (!text && this.$copyWithEmptySelection) {
        copyLine = true;
        var ranges = this.selection.getAllRanges();
        for (var i = 0; i < ranges.length; i++) {
          var range = ranges[i];
          if (i && ranges[i - 1].start.row == range.start.row) continue;
          text += this.session.getLine(range.start.row) + nl;
        }
      }
      var e = { text: text };
      this._signal("copy", e);
      clipboard.lineMode = copyLine ? e.text : false;
      return e.text;
    };
    Editor.prototype.onCopy = function () {
      this.commands.exec("copy", this);
    };
    Editor.prototype.onCut = function () {
      this.commands.exec("cut", this);
    };
    Editor.prototype.onPaste = function (text, event) {
      var e = { text: text, event: event };
      this.commands.exec("paste", this, e);
    };
    Editor.prototype.$handlePaste = function (e) {
      if (typeof e == "string") e = { text: e };
      this._signal("paste", e);
      var text = e.text;
      var lineMode = text === clipboard.lineMode;
      var session = this.session;
      if (!this.inMultiSelectMode || this.inVirtualSelectionMode) {
        if (lineMode)
          session.insert({ row: this.selection.lead.row, column: 0 }, text);
        else this.insert(text);
      } else if (lineMode) {
        this.selection.rangeList.ranges.forEach(function (range) {
          session.insert({ row: range.start.row, column: 0 }, text);
        });
      } else {
        var lines = text.split(/\r\n|\r|\n/);
        var ranges = this.selection.rangeList.ranges;
        var isFullLine = lines.length == 2 && (!lines[0] || !lines[1]);
        if (lines.length != ranges.length || isFullLine)
          return this.commands.exec("insertstring", this, text);
        for (var i = ranges.length; i--; ) {
          var range = ranges[i];
          if (!range.isEmpty()) session.remove(range);
          session.insert(range.start, lines[i]);
        }
      }
    };
    Editor.prototype.execCommand = function (command, args) {
      return this.commands.exec(command, this, args);
    };
    Editor.prototype.insert = function (text, pasted) {
      var session = this.session;
      var mode = session.getMode();
      var cursor = this.getCursorPosition();
      if (this.getBehavioursEnabled() && !pasted) {
        var transform = mode.transformAction(
          session.getState(cursor.row),
          "insertion",
          this,
          session,
          text,
        );
        if (transform) {
          if (text !== transform.text) {
            if (!this.inVirtualSelectionMode) {
              this.session.mergeUndoDeltas = false;
              this.mergeNextCommand = false;
            }
          }
          text = transform.text;
        }
      }
      if (text == "\t") text = this.session.getTabString();
      if (!this.selection.isEmpty()) {
        var range = this.getSelectionRange();
        cursor = this.session.remove(range);
        this.clearSelection();
      } else if (this.session.getOverwrite() && text.indexOf("\n") == -1) {
        var range = Range.fromPoints(cursor, cursor);
        range.end.column += text.length;
        this.session.remove(range);
      }
      if (text == "\n" || text == "\r\n") {
        var line = session.getLine(cursor.row);
        if (cursor.column > line.search(/\S|$/)) {
          var d = line.substr(cursor.column).search(/\S|$/);
          session.doc.removeInLine(
            cursor.row,
            cursor.column,
            cursor.column + d,
          );
        }
      }
      this.clearSelection();
      var start = cursor.column;
      var lineState = session.getState(cursor.row);
      var line = session.getLine(cursor.row);
      var shouldOutdent = mode.checkOutdent(lineState, line, text);
      session.insert(cursor, text);
      if (transform && transform.selection) {
        if (transform.selection.length == 2) {
          // Transform relative to the current column
          this.selection.setSelectionRange(
            new Range(
              cursor.row,
              start + transform.selection[0],
              cursor.row,
              start + transform.selection[1],
            ),
          );
        } else {
          // Transform relative to the current row.
          this.selection.setSelectionRange(
            new Range(
              cursor.row + transform.selection[0],
              transform.selection[1],
              cursor.row + transform.selection[2],
              transform.selection[3],
            ),
          );
        }
      }
      if (this.$enableAutoIndent) {
        if (session.getDocument().isNewLine(text)) {
          var lineIndent = mode.getNextLineIndent(
            lineState,
            line.slice(0, cursor.column),
            session.getTabString(),
          );
          session.insert({ row: cursor.row + 1, column: 0 }, lineIndent);
        }
        if (shouldOutdent) mode.autoOutdent(lineState, session, cursor.row);
      }
    };
    Editor.prototype.autoIndent = function () {
      var session = this.session;
      var mode = session.getMode();
      var startRow, endRow;
      if (this.selection.isEmpty()) {
        startRow = 0;
        endRow = session.doc.getLength() - 1;
      } else {
        var selectedRange = this.getSelectionRange();
        startRow = selectedRange.start.row;
        endRow = selectedRange.end.row;
      }
      var prevLineState = "";
      var prevLine = "";
      var lineIndent = "";
      var line, currIndent, range;
      var tab = session.getTabString();
      for (var row = startRow; row <= endRow; row++) {
        if (row > 0) {
          prevLineState = session.getState(row - 1);
          prevLine = session.getLine(row - 1);
          lineIndent = mode.getNextLineIndent(prevLineState, prevLine, tab);
        }
        line = session.getLine(row);
        currIndent = mode.$getIndent(line);
        if (lineIndent !== currIndent) {
          if (currIndent.length > 0) {
            range = new Range(row, 0, row, currIndent.length);
            session.remove(range);
          }
          if (lineIndent.length > 0) {
            session.insert({ row: row, column: 0 }, lineIndent);
          }
        }
        mode.autoOutdent(prevLineState, session, row);
      }
    };
    Editor.prototype.onTextInput = function (text, composition) {
      if (!composition) return this.keyBinding.onTextInput(text);
      this.startOperation({ command: { name: "insertstring" } });
      var applyComposition = this.applyComposition.bind(
        this,
        text,
        composition,
      );
      if (this.selection.rangeCount) this.forEachSelection(applyComposition);
      else applyComposition();
      this.endOperation();
    };
    Editor.prototype.applyComposition = function (text, composition) {
      if (composition.extendLeft || composition.extendRight) {
        var r = this.selection.getRange();
        r.start.column -= composition.extendLeft;
        r.end.column += composition.extendRight;
        if (r.start.column < 0) {
          r.start.row--;
          r.start.column += this.session.getLine(r.start.row).length + 1;
        }
        this.selection.setRange(r);
        if (!text && !r.isEmpty()) this.remove();
      }
      if (text || !this.selection.isEmpty()) this.insert(text, true);
      if (composition.restoreStart || composition.restoreEnd) {
        var r = this.selection.getRange();
        r.start.column -= composition.restoreStart;
        r.end.column -= composition.restoreEnd;
        this.selection.setRange(r);
      }
    };
    Editor.prototype.onCommandKey = function (e, hashId, keyCode) {
      return this.keyBinding.onCommandKey(e, hashId, keyCode);
    };
    Editor.prototype.setOverwrite = function (overwrite) {
      this.session.setOverwrite(overwrite);
    };
    Editor.prototype.getOverwrite = function () {
      return this.session.getOverwrite();
    };
    Editor.prototype.toggleOverwrite = function () {
      this.session.toggleOverwrite();
    };
    Editor.prototype.setScrollSpeed = function (speed) {
      this.setOption("scrollSpeed", speed);
    };
    Editor.prototype.getScrollSpeed = function () {
      return this.getOption("scrollSpeed");
    };
    Editor.prototype.setDragDelay = function (dragDelay) {
      this.setOption("dragDelay", dragDelay);
    };
    Editor.prototype.getDragDelay = function () {
      return this.getOption("dragDelay");
    };
    Editor.prototype.setSelectionStyle = function (val) {
      this.setOption("selectionStyle", val);
    };
    Editor.prototype.getSelectionStyle = function () {
      return this.getOption("selectionStyle");
    };
    Editor.prototype.setHighlightActiveLine = function (shouldHighlight) {
      this.setOption("highlightActiveLine", shouldHighlight);
    };
    Editor.prototype.getHighlightActiveLine = function () {
      return this.getOption("highlightActiveLine");
    };
    Editor.prototype.setHighlightGutterLine = function (shouldHighlight) {
      this.setOption("highlightGutterLine", shouldHighlight);
    };
    Editor.prototype.getHighlightGutterLine = function () {
      return this.getOption("highlightGutterLine");
    };
    Editor.prototype.setHighlightSelectedWord = function (shouldHighlight) {
      this.setOption("highlightSelectedWord", shouldHighlight);
    };
    Editor.prototype.getHighlightSelectedWord = function () {
      return this.$highlightSelectedWord;
    };
    Editor.prototype.setAnimatedScroll = function (shouldAnimate) {
      this.renderer.setAnimatedScroll(shouldAnimate);
    };
    Editor.prototype.getAnimatedScroll = function () {
      return this.renderer.getAnimatedScroll();
    };
    Editor.prototype.setShowInvisibles = function (showInvisibles) {
      this.renderer.setShowInvisibles(showInvisibles);
    };
    Editor.prototype.getShowInvisibles = function () {
      return this.renderer.getShowInvisibles();
    };
    Editor.prototype.setDisplayIndentGuides = function (display) {
      this.renderer.setDisplayIndentGuides(display);
    };
    Editor.prototype.getDisplayIndentGuides = function () {
      return this.renderer.getDisplayIndentGuides();
    };
    Editor.prototype.setHighlightIndentGuides = function (highlight) {
      this.renderer.setHighlightIndentGuides(highlight);
    };
    Editor.prototype.getHighlightIndentGuides = function () {
      return this.renderer.getHighlightIndentGuides();
    };
    Editor.prototype.setShowPrintMargin = function (showPrintMargin) {
      this.renderer.setShowPrintMargin(showPrintMargin);
    };
    Editor.prototype.getShowPrintMargin = function () {
      return this.renderer.getShowPrintMargin();
    };
    Editor.prototype.setPrintMarginColumn = function (showPrintMargin) {
      this.renderer.setPrintMarginColumn(showPrintMargin);
    };
    Editor.prototype.getPrintMarginColumn = function () {
      return this.renderer.getPrintMarginColumn();
    };
    Editor.prototype.setReadOnly = function (readOnly) {
      this.setOption("readOnly", readOnly);
    };
    Editor.prototype.getReadOnly = function () {
      return this.getOption("readOnly");
    };
    Editor.prototype.setBehavioursEnabled = function (enabled) {
      this.setOption("behavioursEnabled", enabled);
    };
    Editor.prototype.getBehavioursEnabled = function () {
      return this.getOption("behavioursEnabled");
    };
    Editor.prototype.setWrapBehavioursEnabled = function (enabled) {
      this.setOption("wrapBehavioursEnabled", enabled);
    };
    Editor.prototype.getWrapBehavioursEnabled = function () {
      return this.getOption("wrapBehavioursEnabled");
    };
    Editor.prototype.setShowFoldWidgets = function (show) {
      this.setOption("showFoldWidgets", show);
    };
    Editor.prototype.getShowFoldWidgets = function () {
      return this.getOption("showFoldWidgets");
    };
    Editor.prototype.setFadeFoldWidgets = function (fade) {
      this.setOption("fadeFoldWidgets", fade);
    };
    Editor.prototype.getFadeFoldWidgets = function () {
      return this.getOption("fadeFoldWidgets");
    };
    Editor.prototype.remove = function (dir) {
      if (this.selection.isEmpty()) {
        if (dir == "left") this.selection.selectLeft();
        else this.selection.selectRight();
      }
      var range = this.getSelectionRange();
      if (this.getBehavioursEnabled()) {
        var session = this.session;
        var state = session.getState(range.start.row);
        var new_range = session
          .getMode()
          .transformAction(state, "deletion", this, session, range);
        if (range.end.column === 0) {
          var text = session.getTextRange(range);
          if (text[text.length - 1] == "\n") {
            var line = session.getLine(range.end.row);
            if (/^\s+$/.test(line)) {
              range.end.column = line.length;
            }
          }
        }
        if (new_range) range = new_range;
      }
      this.session.remove(range);
      this.clearSelection();
    };
    Editor.prototype.removeWordRight = function () {
      if (this.selection.isEmpty()) this.selection.selectWordRight();
      this.session.remove(this.getSelectionRange());
      this.clearSelection();
    };
    Editor.prototype.removeWordLeft = function () {
      if (this.selection.isEmpty()) this.selection.selectWordLeft();
      this.session.remove(this.getSelectionRange());
      this.clearSelection();
    };
    Editor.prototype.removeToLineStart = function () {
      if (this.selection.isEmpty()) this.selection.selectLineStart();
      if (this.selection.isEmpty()) this.selection.selectLeft();
      this.session.remove(this.getSelectionRange());
      this.clearSelection();
    };
    Editor.prototype.removeToLineEnd = function () {
      if (this.selection.isEmpty()) this.selection.selectLineEnd();
      var range = this.getSelectionRange();
      if (
        range.start.column == range.end.column &&
        range.start.row == range.end.row
      ) {
        range.end.column = 0;
        range.end.row++;
      }
      this.session.remove(range);
      this.clearSelection();
    };
    Editor.prototype.splitLine = function () {
      if (!this.selection.isEmpty()) {
        this.session.remove(this.getSelectionRange());
        this.clearSelection();
      }
      var cursor = this.getCursorPosition();
      this.insert("\n");
      this.moveCursorToPosition(cursor);
    };
    Editor.prototype.setGhostText = function (text, position) {
      if (!this.session.widgetManager) {
        this.session.widgetManager = new LineWidgets(this.session);
        this.session.widgetManager.attach(this);
      }
      this.renderer.setGhostText(text, position);
    };
    Editor.prototype.removeGhostText = function () {
      if (!this.session.widgetManager) return;
      this.renderer.removeGhostText();
    };
    Editor.prototype.transposeLetters = function () {
      if (!this.selection.isEmpty()) {
        return;
      }
      var cursor = this.getCursorPosition();
      var column = cursor.column;
      if (column === 0) return;
      var line = this.session.getLine(cursor.row);
      var swap, range;
      if (column < line.length) {
        swap = line.charAt(column) + line.charAt(column - 1);
        range = new Range(cursor.row, column - 1, cursor.row, column + 1);
      } else {
        swap = line.charAt(column - 1) + line.charAt(column - 2);
        range = new Range(cursor.row, column - 2, cursor.row, column);
      }
      this.session.replace(range, swap);
      this.session.selection.moveToPosition(range.end);
    };
    Editor.prototype.toLowerCase = function () {
      var originalRange = this.getSelectionRange();
      if (this.selection.isEmpty()) {
        this.selection.selectWord();
      }
      var range = this.getSelectionRange();
      var text = this.session.getTextRange(range);
      this.session.replace(range, text.toLowerCase());
      this.selection.setSelectionRange(originalRange);
    };
    Editor.prototype.toUpperCase = function () {
      var originalRange = this.getSelectionRange();
      if (this.selection.isEmpty()) {
        this.selection.selectWord();
      }
      var range = this.getSelectionRange();
      var text = this.session.getTextRange(range);
      this.session.replace(range, text.toUpperCase());
      this.selection.setSelectionRange(originalRange);
    };
    Editor.prototype.indent = function () {
      var session = this.session;
      var range = this.getSelectionRange();
      if (range.start.row < range.end.row) {
        var rows = this.$getSelectedRows();
        session.indentRows(rows.first, rows.last, "\t");
        return;
      } else if (range.start.column < range.end.column) {
        var text = session.getTextRange(range);
        if (!/^\s+$/.test(text)) {
          var rows = this.$getSelectedRows();
          session.indentRows(rows.first, rows.last, "\t");
          return;
        }
      }
      var line = session.getLine(range.start.row);
      var position = range.start;
      var size = session.getTabSize();
      var column = session.documentToScreenColumn(
        position.row,
        position.column,
      );
      if (this.session.getUseSoftTabs()) {
        var count = size - (column % size);
        var indentString = lang.stringRepeat(" ", count);
      } else {
        var count = column % size;
        while (line[range.start.column - 1] == " " && count) {
          range.start.column--;
          count--;
        }
        this.selection.setSelectionRange(range);
        indentString = "\t";
      }
      return this.insert(indentString);
    };
    Editor.prototype.blockIndent = function () {
      var rows = this.$getSelectedRows();
      this.session.indentRows(rows.first, rows.last, "\t");
    };
    Editor.prototype.blockOutdent = function () {
      var selection = this.session.getSelection();
      this.session.outdentRows(selection.getRange());
    };
    Editor.prototype.sortLines = function () {
      var rows = this.$getSelectedRows();
      var session = this.session;
      var lines = [];
      for (var i = rows.first; i <= rows.last; i++)
        lines.push(session.getLine(i));
      lines.sort(function (a, b) {
        if (a.toLowerCase() < b.toLowerCase()) return -1;
        if (a.toLowerCase() > b.toLowerCase()) return 1;
        return 0;
      });
      var deleteRange = new Range(0, 0, 0, 0);
      for (var i = rows.first; i <= rows.last; i++) {
        var line = session.getLine(i);
        deleteRange.start.row = i;
        deleteRange.end.row = i;
        deleteRange.end.column = line.length;
        session.replace(deleteRange, lines[i - rows.first]);
      }
    };
    Editor.prototype.toggleCommentLines = function () {
      var state = this.session.getState(this.getCursorPosition().row);
      var rows = this.$getSelectedRows();
      this.session
        .getMode()
        .toggleCommentLines(state, this.session, rows.first, rows.last);
    };
    Editor.prototype.toggleBlockComment = function () {
      var cursor = this.getCursorPosition();
      var state = this.session.getState(cursor.row);
      var range = this.getSelectionRange();
      this.session
        .getMode()
        .toggleBlockComment(state, this.session, range, cursor);
    };
    Editor.prototype.getNumberAt = function (row, column) {
      var _numberRx = /[\-]?[0-9]+(?:\.[0-9]+)?/g;
      _numberRx.lastIndex = 0;
      var s = this.session.getLine(row);
      while (_numberRx.lastIndex < column) {
        var m = _numberRx.exec(s);
        if (m.index <= column && m.index + m[0].length >= column) {
          var number = {
            value: m[0],
            start: m.index,
            end: m.index + m[0].length,
          };
          return number;
        }
      }
      return null;
    };
    Editor.prototype.modifyNumber = function (amount) {
      var row = this.selection.getCursor().row;
      var column = this.selection.getCursor().column;
      var charRange = new Range(row, column - 1, row, column);
      var c = this.session.getTextRange(charRange);
      if (!isNaN(parseFloat(c)) && isFinite(c)) {
        var nr = this.getNumberAt(row, column);
        if (nr) {
          var fp =
            nr.value.indexOf(".") >= 0
              ? nr.start + nr.value.indexOf(".") + 1
              : nr.end;
          var decimals = nr.start + nr.value.length - fp;
          var t = parseFloat(nr.value);
          t *= Math.pow(10, decimals);
          if (fp !== nr.end && column < fp) {
            amount *= Math.pow(10, nr.end - column - 1);
          } else {
            amount *= Math.pow(10, nr.end - column);
          }
          t += amount;
          t /= Math.pow(10, decimals);
          var nnr = t.toFixed(decimals);
          var replaceRange = new Range(row, nr.start, row, nr.end);
          this.session.replace(replaceRange, nnr);
          this.moveCursorTo(
            row,
            Math.max(nr.start + 1, column + nnr.length - nr.value.length),
          );
        }
      } else {
        this.toggleWord();
      }
    };
    Editor.prototype.toggleWord = function () {
      var row = this.selection.getCursor().row;
      var column = this.selection.getCursor().column;
      this.selection.selectWord();
      var currentState = this.getSelectedText();
      var currWordStart = this.selection.getWordRange().start.column;
      var wordParts = currentState
        .replace(/([a-z]+|[A-Z]+)(?=[A-Z_]|$)/g, "$1 ")
        .split(/\s/);
      var delta = column - currWordStart - 1;
      if (delta < 0) delta = 0;
      var curLength = 0,
        itLength = 0;
      var that = this;
      if (currentState.match(/[A-Za-z0-9_]+/)) {
        wordParts.forEach(function (item, i) {
          itLength = curLength + item.length;
          if (delta >= curLength && delta <= itLength) {
            currentState = item;
            that.selection.clearSelection();
            that.moveCursorTo(row, curLength + currWordStart);
            that.selection.selectTo(row, itLength + currWordStart);
          }
          curLength = itLength;
        });
      }
      var wordPairs = this.$toggleWordPairs;
      var reg;
      for (var i = 0; i < wordPairs.length; i++) {
        var item = wordPairs[i];
        for (var j = 0; j <= 1; j++) {
          var negate = +!j;
          var firstCondition = currentState.match(
            new RegExp("^\\s?_?(" + lang.escapeRegExp(item[j]) + ")\\s?$", "i"),
          );
          if (firstCondition) {
            var secondCondition = currentState.match(
              new RegExp(
                "([_]|^|\\s)(" +
                  lang.escapeRegExp(firstCondition[1]) +
                  ")($|\\s)",
                "g",
              ),
            );
            if (secondCondition) {
              reg = currentState.replace(
                new RegExp(lang.escapeRegExp(item[j]), "i"),
                function (result) {
                  var res = item[negate];
                  if (result.toUpperCase() == result) {
                    res = res.toUpperCase();
                  } else if (
                    result.charAt(0).toUpperCase() == result.charAt(0)
                  ) {
                    res =
                      res.substr(0, 0) +
                      item[negate].charAt(0).toUpperCase() +
                      res.substr(1);
                  }
                  return res;
                },
              );
              this.insert(reg);
              reg = "";
            }
          }
        }
      }
    };
    Editor.prototype.findLinkAt = function (row, column) {
      var e_1, _a;
      var line = this.session.getLine(row);
      var wordParts = line.split(/((?:https?|ftp):\/\/[\S]+)/);
      var columnPosition = column;
      if (columnPosition < 0) columnPosition = 0;
      var previousPosition = 0,
        currentPosition = 0,
        match;
      try {
        for (
          var wordParts_1 = __values(wordParts),
            wordParts_1_1 = wordParts_1.next();
          !wordParts_1_1.done;
          wordParts_1_1 = wordParts_1.next()
        ) {
          var item = wordParts_1_1.value;
          currentPosition = previousPosition + item.length;
          if (
            columnPosition >= previousPosition &&
            columnPosition <= currentPosition
          ) {
            if (item.match(/((?:https?|ftp):\/\/[\S]+)/)) {
              match = item.replace(/[\s:.,'";}\]]+$/, "");
              break;
            }
          }
          previousPosition = currentPosition;
        }
      } catch (e_1_1) {
        e_1 = { error: e_1_1 };
      } finally {
        try {
          if (wordParts_1_1 && !wordParts_1_1.done && (_a = wordParts_1.return))
            _a.call(wordParts_1);
        } finally {
          if (e_1) throw e_1.error;
        }
      }
      return match;
    };
    Editor.prototype.openLink = function () {
      var cursor = this.selection.getCursor();
      var url = this.findLinkAt(cursor.row, cursor.column);
      if (url) window.open(url, "_blank");
      return url != null;
    };
    Editor.prototype.removeLines = function () {
      var rows = this.$getSelectedRows();
      this.session.removeFullLines(rows.first, rows.last);
      this.clearSelection();
    };
    Editor.prototype.duplicateSelection = function () {
      var sel = this.selection;
      var doc = this.session;
      var range = sel.getRange();
      var reverse = sel.isBackwards();
      if (range.isEmpty()) {
        var row = range.start.row;
        doc.duplicateLines(row, row);
      } else {
        var point = reverse ? range.start : range.end;
        var endPoint = doc.insert(point, doc.getTextRange(range));
        range.start = point;
        range.end = endPoint;
        sel.setSelectionRange(range, reverse);
      }
    };
    Editor.prototype.moveLinesDown = function () {
      this.$moveLines(1, false);
    };
    Editor.prototype.moveLinesUp = function () {
      this.$moveLines(-1, false);
    };
    Editor.prototype.moveText = function (range, toPosition, copy) {
      return this.session.moveText(range, toPosition, copy);
    };
    Editor.prototype.copyLinesUp = function () {
      this.$moveLines(-1, true);
    };
    Editor.prototype.copyLinesDown = function () {
      this.$moveLines(1, true);
    };
    Editor.prototype.$moveLines = function (dir, copy) {
      var rows, moved;
      var selection = this.selection;
      if (!selection.inMultiSelectMode || this.inVirtualSelectionMode) {
        var range = selection.toOrientedRange();
        rows = this.$getSelectedRows(range);
        moved = this.session.$moveLines(rows.first, rows.last, copy ? 0 : dir);
        if (copy && dir == -1) moved = 0;
        range.moveBy(moved, 0);
        selection.fromOrientedRange(range);
      } else {
        var ranges = selection.rangeList.ranges;
        selection.rangeList.detach(this.session);
        this.inVirtualSelectionMode = true;
        var diff = 0;
        var totalDiff = 0;
        var l = ranges.length;
        for (var i = 0; i < l; i++) {
          var rangeIndex = i;
          ranges[i].moveBy(diff, 0);
          rows = this.$getSelectedRows(ranges[i]);
          var first = rows.first;
          var last = rows.last;
          while (++i < l) {
            if (totalDiff) ranges[i].moveBy(totalDiff, 0);
            var subRows = this.$getSelectedRows(ranges[i]);
            if (copy && subRows.first != last) break;
            else if (!copy && subRows.first > last + 1) break;
            last = subRows.last;
          }
          i--;
          diff = this.session.$moveLines(first, last, copy ? 0 : dir);
          if (copy && dir == -1) rangeIndex = i + 1;
          while (rangeIndex <= i) {
            ranges[rangeIndex].moveBy(diff, 0);
            rangeIndex++;
          }
          if (!copy) diff = 0;
          totalDiff += diff;
        }
        selection.fromOrientedRange(selection.ranges[0]);
        selection.rangeList.attach(this.session);
        this.inVirtualSelectionMode = false;
      }
    };
    Editor.prototype.$getSelectedRows = function (range) {
      range = (range || this.getSelectionRange()).collapseRows();
      return {
        first: this.session.getRowFoldStart(range.start.row),
        last: this.session.getRowFoldEnd(range.end.row),
      };
    };
    Editor.prototype.onCompositionStart = function (compositionState) {
      this.renderer.showComposition(compositionState);
    };
    Editor.prototype.onCompositionUpdate = function (text) {
      this.renderer.setCompositionText(text);
    };
    Editor.prototype.onCompositionEnd = function () {
      this.renderer.hideComposition();
    };
    Editor.prototype.getFirstVisibleRow = function () {
      return this.renderer.getFirstVisibleRow();
    };
    Editor.prototype.getLastVisibleRow = function () {
      return this.renderer.getLastVisibleRow();
    };
    Editor.prototype.isRowVisible = function (row) {
      return (
        row >= this.getFirstVisibleRow() && row <= this.getLastVisibleRow()
      );
    };
    Editor.prototype.isRowFullyVisible = function (row) {
      return (
        row >= this.renderer.getFirstFullyVisibleRow() &&
        row <= this.renderer.getLastFullyVisibleRow()
      );
    };
    Editor.prototype.$getVisibleRowCount = function () {
      return (
        this.renderer.getScrollBottomRow() - this.renderer.getScrollTopRow() + 1
      );
    };
    Editor.prototype.$moveByPage = function (dir, select) {
      var renderer = this.renderer;
      var config = this.renderer.layerConfig;
      var rows = dir * Math.floor(config.height / config.lineHeight);
      if (select === true) {
        this.selection.$moveSelection(function () {
          this.moveCursorBy(rows, 0);
        });
      } else if (select === false) {
        this.selection.moveCursorBy(rows, 0);
        this.selection.clearSelection();
      }
      var scrollTop = renderer.scrollTop;
      renderer.scrollBy(0, rows * config.lineHeight);
      if (select != null) renderer.scrollCursorIntoView(null, 0.5);
      renderer.animateScrolling(scrollTop);
    };
    Editor.prototype.selectPageDown = function () {
      this.$moveByPage(1, true);
    };
    Editor.prototype.selectPageUp = function () {
      this.$moveByPage(-1, true);
    };
    Editor.prototype.gotoPageDown = function () {
      this.$moveByPage(1, false);
    };
    Editor.prototype.gotoPageUp = function () {
      this.$moveByPage(-1, false);
    };
    Editor.prototype.scrollPageDown = function () {
      this.$moveByPage(1);
    };
    Editor.prototype.scrollPageUp = function () {
      this.$moveByPage(-1);
    };
    Editor.prototype.scrollToRow = function (row) {
      this.renderer.scrollToRow(row);
    };
    Editor.prototype.scrollToLine = function (line, center, animate, callback) {
      this.renderer.scrollToLine(line, center, animate, callback);
    };
    Editor.prototype.centerSelection = function () {
      var range = this.getSelectionRange();
      var pos = {
        row: Math.floor(
          range.start.row + (range.end.row - range.start.row) / 2,
        ),
        column: Math.floor(
          range.start.column + (range.end.column - range.start.column) / 2,
        ),
      };
      this.renderer.alignCursor(pos, 0.5);
    };
    Editor.prototype.getCursorPosition = function () {
      return this.selection.getCursor();
    };
    Editor.prototype.getCursorPositionScreen = function () {
      return this.session.documentToScreenPosition(this.getCursorPosition());
    };
    Editor.prototype.getSelectionRange = function () {
      return this.selection.getRange();
    };
    Editor.prototype.selectAll = function () {
      this.selection.selectAll();
    };
    Editor.prototype.clearSelection = function () {
      this.selection.clearSelection();
    };
    Editor.prototype.moveCursorTo = function (row, column) {
      this.selection.moveCursorTo(row, column);
    };
    Editor.prototype.moveCursorToPosition = function (pos) {
      this.selection.moveCursorToPosition(pos);
    };
    Editor.prototype.jumpToMatching = function (select, expand) {
      var cursor = this.getCursorPosition();
      var iterator = new TokenIterator(this.session, cursor.row, cursor.column);
      var prevToken = iterator.getCurrentToken();
      var tokenCount = 0;
      if (prevToken && prevToken.type.indexOf("tag-name") !== -1) {
        prevToken = iterator.stepBackward();
      }
      var token = prevToken || iterator.stepForward();
      if (!token) return;
      var matchType;
      var found = false;
      var depth = {};
      var i = cursor.column - token.start;
      var bracketType;
      var brackets = {
        ")": "(",
        "(": "(",
        "]": "[",
        "[": "[",
        "{": "{",
        "}": "{",
      };
      do {
        if (token.value.match(/[{}()\[\]]/g)) {
          for (; i < token.value.length && !found; i++) {
            if (!brackets[token.value[i]]) {
              continue;
            }
            bracketType =
              brackets[token.value[i]] +
              "." +
              token.type.replace("rparen", "lparen");
            if (isNaN(depth[bracketType])) {
              depth[bracketType] = 0;
            }
            switch (token.value[i]) {
              case "(":
              case "[":
              case "{":
                depth[bracketType]++;
                break;
              case ")":
              case "]":
              case "}":
                depth[bracketType]--;
                if (depth[bracketType] === -1) {
                  matchType = "bracket";
                  found = true;
                }
                break;
            }
          }
        } else if (token.type.indexOf("tag-name") !== -1) {
          if (isNaN(depth[token.value])) {
            depth[token.value] = 0;
          }
          if (prevToken.value === "<" && tokenCount > 1) {
            depth[token.value]++;
          } else if (prevToken.value === "</") {
            depth[token.value]--;
          }
          if (depth[token.value] === -1) {
            matchType = "tag";
            found = true;
          }
        }
        if (!found) {
          prevToken = token;
          tokenCount++;
          token = iterator.stepForward();
          i = 0;
        }
      } while (token && !found);
      if (!matchType) return;
      var range, pos;
      if (matchType === "bracket") {
        range = this.session.getBracketRange(cursor);
        if (!range) {
          range = new Range(
            iterator.getCurrentTokenRow(),
            iterator.getCurrentTokenColumn() + i - 1,
            iterator.getCurrentTokenRow(),
            iterator.getCurrentTokenColumn() + i - 1,
          );
          pos = range.start;
          if (
            expand ||
            (pos.row === cursor.row && Math.abs(pos.column - cursor.column) < 2)
          )
            range = this.session.getBracketRange(pos);
        }
      } else if (matchType === "tag") {
        if (!token || token.type.indexOf("tag-name") === -1) return;
        range = new Range(
          iterator.getCurrentTokenRow(),
          iterator.getCurrentTokenColumn() - 2,
          iterator.getCurrentTokenRow(),
          iterator.getCurrentTokenColumn() - 2,
        );
        if (range.compare(cursor.row, cursor.column) === 0) {
          var tagsRanges = this.session.getMatchingTags(cursor);
          if (tagsRanges) {
            if (tagsRanges.openTag.contains(cursor.row, cursor.column)) {
              range = tagsRanges.closeTag;
              pos = range.start;
            } else {
              range = tagsRanges.openTag;
              if (
                tagsRanges.closeTag.start.row === cursor.row &&
                tagsRanges.closeTag.start.column === cursor.column
              )
                pos = range.end;
              else pos = range.start;
            }
          }
        }
        pos = pos || range.start;
      }
      pos = (range && range.cursor) || pos;
      if (pos) {
        if (select) {
          if (range && expand) {
            this.selection.setRange(range);
          } else if (range && range.isEqual(this.getSelectionRange())) {
            this.clearSelection();
          } else {
            this.selection.selectTo(pos.row, pos.column);
          }
        } else {
          this.selection.moveTo(pos.row, pos.column);
        }
      }
    };
    Editor.prototype.gotoLine = function (lineNumber, column, animate) {
      this.selection.clearSelection();
      this.session.unfold({ row: lineNumber - 1, column: column || 0 });
      this.exitMultiSelectMode && this.exitMultiSelectMode();
      this.moveCursorTo(lineNumber - 1, column || 0);
      if (!this.isRowFullyVisible(lineNumber - 1))
        this.scrollToLine(lineNumber - 1, true, animate);
    };
    Editor.prototype.navigateTo = function (row, column) {
      this.selection.moveTo(row, column);
    };
    Editor.prototype.navigateUp = function (times) {
      if (this.selection.isMultiLine() && !this.selection.isBackwards()) {
        var selectionStart = this.selection.anchor.getPosition();
        return this.moveCursorToPosition(selectionStart);
      }
      this.selection.clearSelection();
      this.selection.moveCursorBy(-times || -1, 0);
    };
    Editor.prototype.navigateDown = function (times) {
      if (this.selection.isMultiLine() && this.selection.isBackwards()) {
        var selectionEnd = this.selection.anchor.getPosition();
        return this.moveCursorToPosition(selectionEnd);
      }
      this.selection.clearSelection();
      this.selection.moveCursorBy(times || 1, 0);
    };
    Editor.prototype.navigateLeft = function (times) {
      if (!this.selection.isEmpty()) {
        var selectionStart = this.getSelectionRange().start;
        this.moveCursorToPosition(selectionStart);
      } else {
        times = times || 1;
        while (times--) {
          this.selection.moveCursorLeft();
        }
      }
      this.clearSelection();
    };
    Editor.prototype.navigateRight = function (times) {
      if (!this.selection.isEmpty()) {
        var selectionEnd = this.getSelectionRange().end;
        this.moveCursorToPosition(selectionEnd);
      } else {
        times = times || 1;
        while (times--) {
          this.selection.moveCursorRight();
        }
      }
      this.clearSelection();
    };
    Editor.prototype.navigateLineStart = function () {
      this.selection.moveCursorLineStart();
      this.clearSelection();
    };
    Editor.prototype.navigateLineEnd = function () {
      this.selection.moveCursorLineEnd();
      this.clearSelection();
    };
    Editor.prototype.navigateFileEnd = function () {
      this.selection.moveCursorFileEnd();
      this.clearSelection();
    };
    Editor.prototype.navigateFileStart = function () {
      this.selection.moveCursorFileStart();
      this.clearSelection();
    };
    Editor.prototype.navigateWordRight = function () {
      this.selection.moveCursorWordRight();
      this.clearSelection();
    };
    Editor.prototype.navigateWordLeft = function () {
      this.selection.moveCursorWordLeft();
      this.clearSelection();
    };
    Editor.prototype.replace = function (replacement, options) {
      if (options) this.$search.set(options);
      var range = this.$search.find(this.session);
      var replaced = 0;
      if (!range) return replaced;
      if (this.$tryReplace(range, replacement)) {
        replaced = 1;
      }
      this.selection.setSelectionRange(range);
      this.renderer.scrollSelectionIntoView(range.start, range.end);
      return replaced;
    };
    Editor.prototype.replaceAll = function (replacement, options) {
      if (options) {
        this.$search.set(options);
      }
      var ranges = this.$search.findAll(this.session);
      var replaced = 0;
      if (!ranges.length) return replaced;
      var selection = this.getSelectionRange();
      this.selection.moveTo(0, 0);
      for (var i = ranges.length - 1; i >= 0; --i) {
        if (this.$tryReplace(ranges[i], replacement)) {
          replaced++;
        }
      }
      this.selection.setSelectionRange(selection);
      return replaced;
    };
    Editor.prototype.$tryReplace = function (range, replacement) {
      var input = this.session.getTextRange(range);
      replacement = this.$search.replace(input, replacement);
      if (replacement !== null) {
        range.end = this.session.replace(range, replacement);
        return range;
      } else {
        return null;
      }
    };
    Editor.prototype.getLastSearchOptions = function () {
      return this.$search.getOptions();
    };
    Editor.prototype.find = function (needle, options, animate) {
      if (!options) options = {};
      if (typeof needle == "string" || needle instanceof RegExp)
        options.needle = needle;
      else if (typeof needle == "object") oop.mixin(options, needle);
      var range = this.selection.getRange();
      if (options.needle == null) {
        needle =
          this.session.getTextRange(range) || this.$search.$options.needle;
        if (!needle) {
          range = this.session.getWordRange(
            range.start.row,
            range.start.column,
          );
          needle = this.session.getTextRange(range);
        }
        this.$search.set({ needle: needle });
      }
      this.$search.set(options);
      if (!options.start) this.$search.set({ start: range });
      var newRange = this.$search.find(this.session);
      if (options.preventScroll) return newRange;
      if (newRange) {
        this.revealRange(newRange, animate);
        return newRange;
      }
      if (options.backwards) range.start = range.end;
      else range.end = range.start;
      this.selection.setRange(range);
    };
    Editor.prototype.findNext = function (options, animate) {
      this.find({ skipCurrent: true, backwards: false }, options, animate);
    };
    Editor.prototype.findPrevious = function (options, animate) {
      this.find(options, { skipCurrent: true, backwards: true }, animate);
    };
    Editor.prototype.revealRange = function (range, animate) {
      this.session.unfold(range);
      this.selection.setSelectionRange(range);
      var scrollTop = this.renderer.scrollTop;
      this.renderer.scrollSelectionIntoView(range.start, range.end, 0.5);
      if (animate !== false) this.renderer.animateScrolling(scrollTop);
    };
    Editor.prototype.undo = function () {
      this.session.getUndoManager().undo(this.session);
      this.renderer.scrollCursorIntoView(null, 0.5);
    };
    Editor.prototype.redo = function () {
      this.session.getUndoManager().redo(this.session);
      this.renderer.scrollCursorIntoView(null, 0.5);
    };
    Editor.prototype.destroy = function () {
      if (this.$toDestroy) {
        this.$toDestroy.forEach(function (el) {
          el.destroy();
        });
        this.$toDestroy = null;
      }
      if (this.$mouseHandler) this.$mouseHandler.destroy();
      this.renderer.destroy();
      this._signal("destroy", this);
      if (this.session) this.session.destroy();
      if (this._$emitInputEvent) this._$emitInputEvent.cancel();
      this.removeAllListeners();
    };
    Editor.prototype.setAutoScrollEditorIntoView = function (enable) {
      if (!enable) return;
      var rect;
      var self = this;
      var shouldScroll = false;
      if (!this.$scrollAnchor)
        this.$scrollAnchor = document.createElement("div");
      var scrollAnchor = this.$scrollAnchor;
      scrollAnchor.style.cssText = "position:absolute";
      this.container.insertBefore(scrollAnchor, this.container.firstChild);
      var onChangeSelection = this.on("changeSelection", function () {
        shouldScroll = true;
      });
      var onBeforeRender = this.renderer.on("beforeRender", function () {
        if (shouldScroll)
          rect = self.renderer.container.getBoundingClientRect();
      });
      var onAfterRender = this.renderer.on("afterRender", function () {
        if (
          shouldScroll &&
          rect &&
          (self.isFocused() || (self.searchBox && self.searchBox.isFocused()))
        ) {
          var renderer = self.renderer;
          var pos = renderer.$cursorLayer.$pixelPos;
          var config = renderer.layerConfig;
          var top = pos.top - config.offset;
          if (pos.top >= 0 && top + rect.top < 0) {
            shouldScroll = true;
          } else if (
            pos.top < config.height &&
            pos.top + rect.top + config.lineHeight > window.innerHeight
          ) {
            shouldScroll = false;
          } else {
            shouldScroll = null;
          }
          if (shouldScroll != null) {
            scrollAnchor.style.top = top + "px";
            scrollAnchor.style.left = pos.left + "px";
            scrollAnchor.style.height = config.lineHeight + "px";
            scrollAnchor.scrollIntoView(shouldScroll);
          }
          shouldScroll = rect = null;
        }
      });
      this.setAutoScrollEditorIntoView = function (enable) {
        if (enable) return;
        delete this.setAutoScrollEditorIntoView;
        this.off("changeSelection", onChangeSelection);
        this.renderer.off("afterRender", onAfterRender);
        this.renderer.off("beforeRender", onBeforeRender);
      };
    };
    Editor.prototype.$resetCursorStyle = function () {
      var style = this.$cursorStyle || "ace";
      var cursorLayer = this.renderer.$cursorLayer;
      if (!cursorLayer) return;
      cursorLayer.setSmoothBlinking(/smooth/.test(style));
      cursorLayer.isBlinking = !this.$readOnly && style != "wide";
      dom.setCssClass(
        cursorLayer.element,
        "ace_slim-cursors",
        /slim/.test(style),
      );
    };
    Editor.prototype.prompt = function (message, options, callback) {
      var editor = this;
      config.loadModule("ace/ext/prompt", function (module) {
        module.prompt(editor, message, options, callback);
      });
    };
    return Editor;
  })();
  Editor.$uid = 0;
  Editor.prototype.curOp = null;
  Editor.prototype.prevOp = {};
  Editor.prototype.$mergeableCommands = ["backspace", "del", "insertstring"];
  Editor.prototype.$toggleWordPairs = [
    ["first", "last"],
    ["true", "false"],
    ["yes", "no"],
    ["width", "height"],
    ["top", "bottom"],
    ["right", "left"],
    ["on", "off"],
    ["x", "y"],
    ["get", "set"],
    ["max", "min"],
    ["horizontal", "vertical"],
    ["show", "hide"],
    ["add", "remove"],
    ["up", "down"],
    ["before", "after"],
    ["even", "odd"],
    ["in", "out"],
    ["inside", "outside"],
    ["next", "previous"],
    ["increase", "decrease"],
    ["attach", "detach"],
    ["&&", "||"],
    ["==", "!="],
  ];
  oop.implement(Editor.prototype, EventEmitter);
  config.defineOptions(Editor.prototype, "editor", {
    selectionStyle: {
      set: function (style) {
        this.onSelectionChange();
        this._signal("changeSelectionStyle", { data: style });
      },
      initialValue: "line",
    },
    highlightActiveLine: {
      set: function () {
        this.$updateHighlightActiveLine();
      },
      initialValue: true,
    },
    highlightSelectedWord: {
      set: function (shouldHighlight) {
        this.$onSelectionChange();
      },
      initialValue: true,
    },
    readOnly: {
      set: function (readOnly) {
        this.textInput.setReadOnly(readOnly);
        this.$resetCursorStyle();
      },
      initialValue: false,
    },
    copyWithEmptySelection: {
      set: function (value) {
        this.textInput.setCopyWithEmptySelection(value);
      },
      initialValue: false,
    },
    cursorStyle: {
      set: function (val) {
        this.$resetCursorStyle();
      },
      values: ["ace", "slim", "smooth", "wide"],
      initialValue: "ace",
    },
    mergeUndoDeltas: {
      values: [false, true, "always"],
      initialValue: true,
    },
    behavioursEnabled: { initialValue: true },
    wrapBehavioursEnabled: { initialValue: true },
    enableAutoIndent: { initialValue: true },
    autoScrollEditorIntoView: {
      set: function (val) {
        this.setAutoScrollEditorIntoView(val);
      },
    },
    keyboardHandler: {
      set: function (val) {
        this.setKeyboardHandler(val);
      },
      get: function () {
        return this.$keybindingId;
      },
      handlesSet: true,
    },
    value: {
      set: function (val) {
        this.session.setValue(val);
      },
      get: function () {
        return this.getValue();
      },
      handlesSet: true,
      hidden: true,
    },
    session: {
      set: function (val) {
        this.setSession(val);
      },
      get: function () {
        return this.session;
      },
      handlesSet: true,
      hidden: true,
    },
    showLineNumbers: {
      set: function (show) {
        this.renderer.$gutterLayer.setShowLineNumbers(show);
        this.renderer.$loop.schedule(this.renderer.CHANGE_GUTTER);
        if (show && this.$relativeLineNumbers)
          relativeNumberRenderer.attach(this);
        else relativeNumberRenderer.detach(this);
      },
      initialValue: true,
    },
    relativeLineNumbers: {
      set: function (value) {
        if (this.$showLineNumbers && value) relativeNumberRenderer.attach(this);
        else relativeNumberRenderer.detach(this);
      },
    },
    placeholder: {
      set: function (message) {
        if (!this.$updatePlaceholder) {
          this.$updatePlaceholder = function () {
            var hasValue =
              this.session &&
              (this.renderer.$composition ||
                this.session.getLength() > 1 ||
                this.session.getLine(0).length > 0);
            if (hasValue && this.renderer.placeholderNode) {
              this.renderer.off("afterRender", this.$updatePlaceholder);
              dom.removeCssClass(this.container, "ace_hasPlaceholder");
              this.renderer.placeholderNode.remove();
              this.renderer.placeholderNode = null;
            } else if (!hasValue && !this.renderer.placeholderNode) {
              this.renderer.on("afterRender", this.$updatePlaceholder);
              dom.addCssClass(this.container, "ace_hasPlaceholder");
              var el = dom.createElement("div");
              el.className = "ace_placeholder";
              el.textContent = this.$placeholder || "";
              this.renderer.placeholderNode = el;
              this.renderer.content.appendChild(this.renderer.placeholderNode);
            } else if (!hasValue && this.renderer.placeholderNode) {
              this.renderer.placeholderNode.textContent =
                this.$placeholder || "";
            }
          }.bind(this);
          this.on("input", this.$updatePlaceholder);
        }
        this.$updatePlaceholder();
      },
    },
    enableKeyboardAccessibility: {
      set: function (value) {
        var blurCommand = {
          name: "blurTextInput",
          description:
            "Set focus to the editor content div to allow tabbing through the page",
          bindKey: "Esc",
          exec: function (editor) {
            editor.blur();
            editor.renderer.scroller.focus();
          },
          readOnly: true,
        };
        var focusOnEnterKeyup = function (e) {
          if (
            e.target == this.renderer.scroller &&
            e.keyCode === keys["enter"]
          ) {
            e.preventDefault();
            var row = this.getCursorPosition().row;
            if (!this.isRowVisible(row)) this.scrollToLine(row, true, true);
            this.focus();
          }
        };
        var gutterKeyboardHandler;
        if (value) {
          this.renderer.enableKeyboardAccessibility = true;
          this.renderer.keyboardFocusClassName = "ace_keyboard-focus";
          this.textInput.getElement().setAttribute("tabindex", -1);
          this.textInput.setNumberOfExtraLines(useragent.isWin ? 3 : 0);
          this.renderer.scroller.setAttribute("tabindex", 0);
          this.renderer.scroller.setAttribute("role", "group");
          this.renderer.scroller.setAttribute(
            "aria-roledescription",
            nls("editor"),
          );
          this.renderer.scroller.classList.add(
            this.renderer.keyboardFocusClassName,
          );
          this.renderer.scroller.setAttribute(
            "aria-label",
            nls(
              "Editor content, press Enter to start editing, press Escape to exit",
            ),
          );
          this.renderer.scroller.addEventListener(
            "keyup",
            focusOnEnterKeyup.bind(this),
          );
          this.commands.addCommand(blurCommand);
          this.renderer.$gutter.setAttribute("tabindex", 0);
          this.renderer.$gutter.setAttribute("aria-hidden", false);
          this.renderer.$gutter.setAttribute("role", "group");
          this.renderer.$gutter.setAttribute(
            "aria-roledescription",
            nls("editor"),
          );
          this.renderer.$gutter.setAttribute(
            "aria-label",
            nls(
              "Editor gutter, press Enter to interact with controls using arrow keys, press Escape to exit",
            ),
          );
          this.renderer.$gutter.classList.add(
            this.renderer.keyboardFocusClassName,
          );
          this.renderer.content.setAttribute("aria-hidden", true);
          if (!gutterKeyboardHandler)
            gutterKeyboardHandler = new GutterKeyboardHandler(this);
          gutterKeyboardHandler.addListener();
        } else {
          this.renderer.enableKeyboardAccessibility = false;
          this.textInput.getElement().setAttribute("tabindex", 0);
          this.textInput.setNumberOfExtraLines(0);
          this.renderer.scroller.setAttribute("tabindex", -1);
          this.renderer.scroller.removeAttribute("role");
          this.renderer.scroller.removeAttribute("aria-roledescription");
          this.renderer.scroller.classList.remove(
            this.renderer.keyboardFocusClassName,
          );
          this.renderer.scroller.removeAttribute("aria-label");
          this.renderer.scroller.removeEventListener(
            "keyup",
            focusOnEnterKeyup.bind(this),
          );
          this.commands.removeCommand(blurCommand);
          this.renderer.content.removeAttribute("aria-hidden");
          this.renderer.$gutter.setAttribute("tabindex", -1);
          this.renderer.$gutter.setAttribute("aria-hidden", true);
          this.renderer.$gutter.removeAttribute("role");
          this.renderer.$gutter.removeAttribute("aria-roledescription");
          this.renderer.$gutter.removeAttribute("aria-label");
          this.renderer.$gutter.classList.remove(
            this.renderer.keyboardFocusClassName,
          );
          if (gutterKeyboardHandler) gutterKeyboardHandler.removeListener();
        }
      },
      initialValue: false,
    },
    customScrollbar: "renderer",
    hScrollBarAlwaysVisible: "renderer",
    vScrollBarAlwaysVisible: "renderer",
    highlightGutterLine: "renderer",
    animatedScroll: "renderer",
    showInvisibles: "renderer",
    showPrintMargin: "renderer",
    printMarginColumn: "renderer",
    printMargin: "renderer",
    fadeFoldWidgets: "renderer",
    showFoldWidgets: "renderer",
    displayIndentGuides: "renderer",
    highlightIndentGuides: "renderer",
    showGutter: "renderer",
    fontSize: "renderer",
    fontFamily: "renderer",
    maxLines: "renderer",
    minLines: "renderer",
    scrollPastEnd: "renderer",
    fixedWidthGutter: "renderer",
    theme: "renderer",
    hasCssTransforms: "renderer",
    maxPixelHeight: "renderer",
    useTextareaForIME: "renderer",
    useResizeObserver: "renderer",
    useSvgGutterIcons: "renderer",
    showFoldedAnnotations: "renderer",
    scrollSpeed: "$mouseHandler",
    dragDelay: "$mouseHandler",
    dragEnabled: "$mouseHandler",
    focusTimeout: "$mouseHandler",
    tooltipFollowsMouse: "$mouseHandler",
    firstLineNumber: "session",
    overwrite: "session",
    newLineMode: "session",
    useWorker: "session",
    useSoftTabs: "session",
    navigateWithinSoftTabs: "session",
    tabSize: "session",
    wrap: "session",
    indentedSoftWrap: "session",
    foldStyle: "session",
    mode: "session",
  });
  var relativeNumberRenderer = {
    getText: function (
      /**@type{EditSession}*/ session,
      /**@type{number}*/ row,
    ) {
      return (
        (Math.abs(session.selection.lead.row - row) ||
          row + 1 + (row < 9 ? "\xb7" : "")) + ""
      );
    },
    getWidth: function (session, /**@type{number}*/ lastLineNumber, config) {
      return (
        Math.max(
          lastLineNumber.toString().length,
          (config.lastRow + 1).toString().length,
          2,
        ) * config.characterWidth
      );
    },
    update: function (e, /**@type{Editor}*/ editor) {
      editor.renderer.$loop.schedule(editor.renderer.CHANGE_GUTTER);
    },
    attach: function (/**@type{Editor}*/ editor) {
      editor.renderer.$gutterLayer.$renderer = this;
      editor.on("changeSelection", this.update);
      this.update(null, editor);
    },
    detach: function (/**@type{Editor}*/ editor) {
      if (editor.renderer.$gutterLayer.$renderer == this)
        editor.renderer.$gutterLayer.$renderer = null;
      editor.off("changeSelection", this.update);
      this.update(null, editor);
    },
  };
  exports.Editor = Editor;
});

define("ace/layer/lines", [
  "require",
  "exports",
  "module",
  "ace/lib/dom",
], function (require, exports, module) {
  "use strict";
  var dom = require("../lib/dom");
  var Lines = /** @class */ (function () {
    function Lines(element, canvasHeight) {
      this.element = element;
      this.canvasHeight = canvasHeight || 500000;
      this.element.style.height = this.canvasHeight * 2 + "px";
      this.cells = [];
      this.cellCache = [];
      this.$offsetCoefficient = 0;
    }
    Lines.prototype.moveContainer = function (config) {
      dom.translate(
        this.element,
        0,
        -((config.firstRowScreen * config.lineHeight) % this.canvasHeight) -
          config.offset * this.$offsetCoefficient,
      );
    };
    Lines.prototype.pageChanged = function (oldConfig, newConfig) {
      return (
        Math.floor(
          (oldConfig.firstRowScreen * oldConfig.lineHeight) / this.canvasHeight,
        ) !==
        Math.floor(
          (newConfig.firstRowScreen * newConfig.lineHeight) / this.canvasHeight,
        )
      );
    };
    Lines.prototype.computeLineTop = function (row, config, session) {
      var screenTop = config.firstRowScreen * config.lineHeight;
      var screenPage = Math.floor(screenTop / this.canvasHeight);
      var lineTop = session.documentToScreenRow(row, 0) * config.lineHeight;
      return lineTop - screenPage * this.canvasHeight;
    };
    Lines.prototype.computeLineHeight = function (row, config, session) {
      return config.lineHeight * session.getRowLineCount(row);
    };
    Lines.prototype.getLength = function () {
      return this.cells.length;
    };
    Lines.prototype.get = function (index) {
      return this.cells[index];
    };
    Lines.prototype.shift = function () {
      this.$cacheCell(this.cells.shift());
    };
    Lines.prototype.pop = function () {
      this.$cacheCell(this.cells.pop());
    };
    Lines.prototype.push = function (cell) {
      if (Array.isArray(cell)) {
        this.cells.push.apply(this.cells, cell);
        var fragment = dom.createFragment(this.element);
        for (var i = 0; i < cell.length; i++) {
          fragment.appendChild(cell[i].element);
        }
        this.element.appendChild(fragment);
      } else {
        this.cells.push(cell);
        this.element.appendChild(cell.element);
      }
    };
    Lines.prototype.unshift = function (cell) {
      if (Array.isArray(cell)) {
        this.cells.unshift.apply(this.cells, cell);
        var fragment = dom.createFragment(this.element);
        for (var i = 0; i < cell.length; i++) {
          fragment.appendChild(cell[i].element);
        }
        if (this.element.firstChild)
          this.element.insertBefore(fragment, this.element.firstChild);
        else this.element.appendChild(fragment);
      } else {
        this.cells.unshift(cell);
        this.element.insertAdjacentElement("afterbegin", cell.element);
      }
    };
    Lines.prototype.last = function () {
      if (this.cells.length) return this.cells[this.cells.length - 1];
      else return null;
    };
    Lines.prototype.$cacheCell = function (cell) {
      if (!cell) return;
      cell.element.remove();
      this.cellCache.push(cell);
    };
    Lines.prototype.createCell = function (row, config, session, initElement) {
      var cell = this.cellCache.pop();
      if (!cell) {
        var element = dom.createElement("div");
        if (initElement) initElement(element);
        this.element.appendChild(element);
        cell = {
          element: element,
          text: "",
          row: row,
        };
      }
      cell.row = row;
      return cell;
    };
    return Lines;
  })();
  exports.Lines = Lines;
});

define("ace/layer/gutter", [
  "require",
  "exports",
  "module",
  "ace/lib/dom",
  "ace/lib/oop",
  "ace/lib/lang",
  "ace/lib/event_emitter",
  "ace/layer/lines",
  "ace/config",
], function (require, exports, module) {
  "use strict";
  var dom = require("../lib/dom");
  var oop = require("../lib/oop");
  var lang = require("../lib/lang");
  var EventEmitter = require("../lib/event_emitter").EventEmitter;
  var Lines = require("./lines").Lines;
  var nls = require("../config").nls;
  var Gutter = /** @class */ (function () {
    function Gutter(parentEl) {
      this.element = dom.createElement("div");
      this.element.className = "ace_layer ace_gutter-layer";
      parentEl.appendChild(this.element);
      this.setShowFoldWidgets(this.$showFoldWidgets);
      this.gutterWidth = 0;
      this.$annotations = [];
      this.$updateAnnotations = this.$updateAnnotations.bind(this);
      this.$lines = new Lines(this.element);
      this.$lines.$offsetCoefficient = 1;
    }
    Gutter.prototype.setSession = function (session) {
      if (this.session) this.session.off("change", this.$updateAnnotations);
      this.session = session;
      if (session) session.on("change", this.$updateAnnotations);
    };
    Gutter.prototype.addGutterDecoration = function (row, className) {
      if (window.console)
        console.warn &&
          console.warn("deprecated use session.addGutterDecoration");
      this.session.addGutterDecoration(row, className);
    };
    Gutter.prototype.removeGutterDecoration = function (row, className) {
      if (window.console)
        console.warn &&
          console.warn("deprecated use session.removeGutterDecoration");
      this.session.removeGutterDecoration(row, className);
    };
    Gutter.prototype.setAnnotations = function (annotations) {
      this.$annotations = [];
      for (var i = 0; i < annotations.length; i++) {
        var annotation = annotations[i];
        var row = annotation.row;
        var rowInfo = this.$annotations[row];
        if (!rowInfo) rowInfo = this.$annotations[row] = { text: [], type: [] };
        var annoText = annotation.text;
        var annoType = annotation.type;
        annoText = annoText ? lang.escapeHTML(annoText) : annotation.html || "";
        if (rowInfo.text.indexOf(annoText) === -1) {
          rowInfo.text.push(annoText);
          rowInfo.type.push(annoType);
        }
        var className = annotation.className;
        if (className) rowInfo.className = className;
        else if (annoType == "error") rowInfo.className = " ace_error";
        else if (annoType == "warning" && rowInfo.className != " ace_error")
          rowInfo.className = " ace_warning";
        else if (annoType == "info" && !rowInfo.className)
          rowInfo.className = " ace_info";
      }
    };
    Gutter.prototype.$updateAnnotations = function (delta) {
      if (!this.$annotations.length) return;
      var firstRow = delta.start.row;
      var len = delta.end.row - firstRow;
      if (len === 0) {
      } else if (delta.action == "remove") {
        this.$annotations.splice(firstRow, len + 1, null);
      } else {
        var args = new Array(len + 1);
        args.unshift(firstRow, 1);
        this.$annotations.splice.apply(this.$annotations, args);
      }
    };
    Gutter.prototype.update = function (config) {
      this.config = config;
      var session = this.session;
      var firstRow = config.firstRow;
      var lastRow = Math.min(
        config.lastRow + config.gutterOffset, // needed to compensate for hor scollbar
        session.getLength() - 1,
      );
      this.oldLastRow = lastRow;
      this.config = config;
      this.$lines.moveContainer(config);
      this.$updateCursorRow();
      var fold = session.getNextFoldLine(firstRow);
      var foldStart = fold ? fold.start.row : Infinity;
      var cell = null;
      var index = -1;
      var row = firstRow;
      while (true) {
        if (row > foldStart) {
          row = fold.end.row + 1;
          fold = session.getNextFoldLine(row, fold);
          foldStart = fold ? fold.start.row : Infinity;
        }
        if (row > lastRow) {
          while (this.$lines.getLength() > index + 1) this.$lines.pop();
          break;
        }
        cell = this.$lines.get(++index);
        if (cell) {
          cell.row = row;
        } else {
          cell = this.$lines.createCell(
            row,
            config,
            this.session,
            onCreateCell,
          );
          this.$lines.push(cell);
        }
        this.$renderCell(cell, config, fold, row);
        row++;
      }
      this._signal("afterRender");
      this.$updateGutterWidth(config);
    };
    Gutter.prototype.$updateGutterWidth = function (config) {
      var session = this.session;
      var gutterRenderer = session.gutterRenderer || this.$renderer;
      var firstLineNumber = session.$firstLineNumber;
      var lastLineText = this.$lines.last() ? this.$lines.last().text : "";
      if (this.$fixedWidth || session.$useWrapMode)
        lastLineText = session.getLength() + firstLineNumber - 1;
      var gutterWidth = gutterRenderer
        ? gutterRenderer.getWidth(session, lastLineText, config)
        : lastLineText.toString().length * config.characterWidth;
      var padding = this.$padding || this.$computePadding();
      gutterWidth += padding.left + padding.right;
      if (gutterWidth !== this.gutterWidth && !isNaN(gutterWidth)) {
        this.gutterWidth = gutterWidth;
        this.element.parentNode.style.width = this.element.style.width =
          Math.ceil(this.gutterWidth) + "px";
        this._signal("changeGutterWidth", gutterWidth);
      }
    };
    Gutter.prototype.$updateCursorRow = function () {
      if (!this.$highlightGutterLine) return;
      var position = this.session.selection.getCursor();
      if (this.$cursorRow === position.row) return;
      this.$cursorRow = position.row;
    };
    Gutter.prototype.updateLineHighlight = function () {
      if (!this.$highlightGutterLine) return;
      var row = this.session.selection.cursor.row;
      this.$cursorRow = row;
      if (this.$cursorCell && this.$cursorCell.row == row) return;
      if (this.$cursorCell)
        this.$cursorCell.element.className =
          this.$cursorCell.element.className.replace(
            "ace_gutter-active-line ",
            "",
          );
      var cells = this.$lines.cells;
      this.$cursorCell = null;
      for (var i = 0; i < cells.length; i++) {
        var cell = cells[i];
        if (cell.row >= this.$cursorRow) {
          if (cell.row > this.$cursorRow) {
            var fold = this.session.getFoldLine(this.$cursorRow);
            if (i > 0 && fold && fold.start.row == cells[i - 1].row)
              cell = cells[i - 1];
            else break;
          }
          cell.element.className =
            "ace_gutter-active-line " + cell.element.className;
          this.$cursorCell = cell;
          break;
        }
      }
    };
    Gutter.prototype.scrollLines = function (config) {
      var oldConfig = this.config;
      this.config = config;
      this.$updateCursorRow();
      if (this.$lines.pageChanged(oldConfig, config))
        return this.update(config);
      this.$lines.moveContainer(config);
      var lastRow = Math.min(
        config.lastRow + config.gutterOffset, // needed to compensate for hor scollbar
        this.session.getLength() - 1,
      );
      var oldLastRow = this.oldLastRow;
      this.oldLastRow = lastRow;
      if (!oldConfig || oldLastRow < config.firstRow)
        return this.update(config);
      if (lastRow < oldConfig.firstRow) return this.update(config);
      if (oldConfig.firstRow < config.firstRow)
        for (
          var row = this.session.getFoldedRowCount(
            oldConfig.firstRow,
            config.firstRow - 1,
          );
          row > 0;
          row--
        )
          this.$lines.shift();
      if (oldLastRow > lastRow)
        for (
          var row = this.session.getFoldedRowCount(lastRow + 1, oldLastRow);
          row > 0;
          row--
        )
          this.$lines.pop();
      if (config.firstRow < oldConfig.firstRow) {
        this.$lines.unshift(
          this.$renderLines(config, config.firstRow, oldConfig.firstRow - 1),
        );
      }
      if (lastRow > oldLastRow) {
        this.$lines.push(this.$renderLines(config, oldLastRow + 1, lastRow));
      }
      this.updateLineHighlight();
      this._signal("afterRender");
      this.$updateGutterWidth(config);
    };
    Gutter.prototype.$renderLines = function (config, firstRow, lastRow) {
      var fragment = [];
      var row = firstRow;
      var foldLine = this.session.getNextFoldLine(row);
      var foldStart = foldLine ? foldLine.start.row : Infinity;
      while (true) {
        if (row > foldStart) {
          row = foldLine.end.row + 1;
          foldLine = this.session.getNextFoldLine(row, foldLine);
          foldStart = foldLine ? foldLine.start.row : Infinity;
        }
        if (row > lastRow) break;
        var cell = this.$lines.createCell(
          row,
          config,
          this.session,
          onCreateCell,
        );
        this.$renderCell(cell, config, foldLine, row);
        fragment.push(cell);
        row++;
      }
      return fragment;
    };
    Gutter.prototype.$renderCell = function (cell, config, fold, row) {
      var element = cell.element;
      var session = this.session;
      var textNode = element.childNodes[0];
      var foldWidget = element.childNodes[1];
      var annotationNode = element.childNodes[2];
      var annotationIconNode = annotationNode.firstChild;
      var firstLineNumber = session.$firstLineNumber;
      var breakpoints = session.$breakpoints;
      var decorations = session.$decorations;
      var gutterRenderer = session.gutterRenderer || this.$renderer;
      var foldWidgets = this.$showFoldWidgets && session.foldWidgets;
      var foldStart = fold ? fold.start.row : Number.MAX_VALUE;
      var lineHeight = config.lineHeight + "px";
      var className = this.$useSvgGutterIcons
        ? "ace_gutter-cell_svg-icons "
        : "ace_gutter-cell ";
      var iconClassName = this.$useSvgGutterIcons ? "ace_icon_svg" : "ace_icon";
      var rowText = (
        gutterRenderer
          ? gutterRenderer.getText(session, row)
          : row + firstLineNumber
      ).toString();
      if (this.$highlightGutterLine) {
        if (
          row == this.$cursorRow ||
          (fold &&
            row < this.$cursorRow &&
            row >= foldStart &&
            this.$cursorRow <= fold.end.row)
        ) {
          className += "ace_gutter-active-line ";
          if (this.$cursorCell != cell) {
            if (this.$cursorCell)
              this.$cursorCell.element.className =
                this.$cursorCell.element.className.replace(
                  "ace_gutter-active-line ",
                  "",
                );
            this.$cursorCell = cell;
          }
        }
      }
      if (breakpoints[row]) className += breakpoints[row];
      if (decorations[row]) className += decorations[row];
      if (this.$annotations[row] && row !== foldStart)
        className += this.$annotations[row].className;
      if (foldWidgets) {
        var c = foldWidgets[row];
        if (c == null) c = foldWidgets[row] = session.getFoldWidget(row);
      }
      if (c) {
        var foldClass = "ace_fold-widget ace_" + c;
        var isClosedFold =
          c == "start" && row == foldStart && row < fold.end.row;
        if (isClosedFold) {
          foldClass += " ace_closed";
          var foldAnnotationClass = "";
          var annotationInFold = false;
          for (var i = row + 1; i <= fold.end.row; i++) {
            if (!this.$annotations[i]) continue;
            if (this.$annotations[i].className === " ace_error") {
              annotationInFold = true;
              foldAnnotationClass = " ace_error_fold";
              break;
            }
            if (this.$annotations[i].className === " ace_warning") {
              annotationInFold = true;
              foldAnnotationClass = " ace_warning_fold";
              continue;
            }
          }
          className += foldAnnotationClass;
        } else foldClass += " ace_open";
        if (foldWidget.className != foldClass) foldWidget.className = foldClass;
        dom.setStyle(foldWidget.style, "height", lineHeight);
        dom.setStyle(foldWidget.style, "display", "inline-block");
        foldWidget.setAttribute("role", "button");
        foldWidget.setAttribute("tabindex", "-1");
        var foldRange = session.getFoldWidgetRange(row);
        if (foldRange)
          foldWidget.setAttribute(
            "aria-label",
            nls("Toggle code folding, rows $0 through $1", [
              foldRange.start.row + 1,
              foldRange.end.row + 1,
            ]),
          );
        else {
          if (fold)
            foldWidget.setAttribute(
              "aria-label",
              nls("Toggle code folding, rows $0 through $1", [
                fold.start.row + 1,
                fold.end.row + 1,
              ]),
            );
          else
            foldWidget.setAttribute(
              "aria-label",
              nls("Toggle code folding, row $0", [row + 1]),
            );
        }
        if (isClosedFold) {
          foldWidget.setAttribute("aria-expanded", "false");
          foldWidget.setAttribute("title", nls("Unfold code"));
        } else {
          foldWidget.setAttribute("aria-expanded", "true");
          foldWidget.setAttribute("title", nls("Fold code"));
        }
      } else {
        if (foldWidget) {
          dom.setStyle(foldWidget.style, "display", "none");
          foldWidget.setAttribute("tabindex", "0");
          foldWidget.removeAttribute("role");
          foldWidget.removeAttribute("aria-label");
        }
      }
      if (annotationInFold && this.$showFoldedAnnotations) {
        annotationNode.className = "ace_gutter_annotation";
        annotationIconNode.className = iconClassName;
        annotationIconNode.className += foldAnnotationClass;
        dom.setStyle(annotationIconNode.style, "height", lineHeight);
        dom.setStyle(annotationNode.style, "display", "block");
        dom.setStyle(annotationNode.style, "height", lineHeight);
        annotationNode.setAttribute(
          "aria-label",
          nls("Read annotations row $0", [rowText]),
        );
        annotationNode.setAttribute("tabindex", "-1");
        annotationNode.setAttribute("role", "button");
      } else if (this.$annotations[row]) {
        annotationNode.className = "ace_gutter_annotation";
        annotationIconNode.className = iconClassName;
        if (this.$useSvgGutterIcons)
          annotationIconNode.className += this.$annotations[row].className;
        else
          element.classList.add(
            this.$annotations[row].className.replace(" ", ""),
          );
        dom.setStyle(annotationIconNode.style, "height", lineHeight);
        dom.setStyle(annotationNode.style, "display", "block");
        dom.setStyle(annotationNode.style, "height", lineHeight);
        annotationNode.setAttribute(
          "aria-label",
          nls("Read annotations row $0", [rowText]),
        );
        annotationNode.setAttribute("tabindex", "-1");
        annotationNode.setAttribute("role", "button");
      } else {
        dom.setStyle(annotationNode.style, "display", "none");
        annotationNode.removeAttribute("aria-label");
        annotationNode.removeAttribute("role");
        annotationNode.setAttribute("tabindex", "0");
      }
      if (rowText !== textNode.data) {
        textNode.data = rowText;
      }
      if (element.className != className) element.className = className;
      dom.setStyle(
        cell.element.style,
        "height",
        this.$lines.computeLineHeight(row, config, session) + "px",
      );
      dom.setStyle(
        cell.element.style,
        "top",
        this.$lines.computeLineTop(row, config, session) + "px",
      );
      cell.text = rowText;
      if (
        annotationNode.style.display === "none" &&
        foldWidget.style.display === "none"
      )
        cell.element.setAttribute("aria-hidden", true);
      else cell.element.setAttribute("aria-hidden", false);
      return cell;
    };
    Gutter.prototype.setHighlightGutterLine = function (highlightGutterLine) {
      this.$highlightGutterLine = highlightGutterLine;
    };
    Gutter.prototype.setShowLineNumbers = function (show) {
      this.$renderer = !show && {
        getWidth: function () {
          return 0;
        },
        getText: function () {
          return "";
        },
      };
    };
    Gutter.prototype.getShowLineNumbers = function () {
      return this.$showLineNumbers;
    };
    Gutter.prototype.setShowFoldWidgets = function (show) {
      if (show) dom.addCssClass(this.element, "ace_folding-enabled");
      else dom.removeCssClass(this.element, "ace_folding-enabled");
      this.$showFoldWidgets = show;
      this.$padding = null;
    };
    Gutter.prototype.getShowFoldWidgets = function () {
      return this.$showFoldWidgets;
    };
    Gutter.prototype.$computePadding = function () {
      if (!this.element.firstChild) return { left: 0, right: 0 };
      var style = dom.computedStyle(
        /**@type{Element}*/ (this.element.firstChild),
      );
      this.$padding = {};
      this.$padding.left =
        (parseInt(style.borderLeftWidth) || 0) +
        (parseInt(style.paddingLeft) || 0) +
        1;
      this.$padding.right =
        (parseInt(style.borderRightWidth) || 0) +
        (parseInt(style.paddingRight) || 0);
      return this.$padding;
    };
    Gutter.prototype.getRegion = function (point) {
      var padding = this.$padding || this.$computePadding();
      var rect = this.element.getBoundingClientRect();
      if (point.x < padding.left + rect.left) return "markers";
      if (this.$showFoldWidgets && point.x > rect.right - padding.right)
        return "foldWidgets";
    };
    return Gutter;
  })();
  Gutter.prototype.$fixedWidth = false;
  Gutter.prototype.$highlightGutterLine = true;
  Gutter.prototype.$renderer = "";
  Gutter.prototype.$showLineNumbers = true;
  Gutter.prototype.$showFoldWidgets = true;
  oop.implement(Gutter.prototype, EventEmitter);
  function onCreateCell(element) {
    var textNode = document.createTextNode("");
    element.appendChild(textNode);
    var foldWidget = dom.createElement("span");
    element.appendChild(foldWidget);
    var annotationNode = dom.createElement("span");
    element.appendChild(annotationNode);
    var annotationIconNode = dom.createElement("span");
    annotationNode.appendChild(annotationIconNode);
    return element;
  }
  exports.Gutter = Gutter;
});

define("ace/layer/marker", [
  "require",
  "exports",
  "module",
  "ace/range",
  "ace/lib/dom",
], function (require, exports, module) {
  "use strict";
  var Range = require("../range").Range;
  var dom = require("../lib/dom");
  var Marker = /** @class */ (function () {
    function Marker(parentEl) {
      this.element = dom.createElement("div");
      this.element.className = "ace_layer ace_marker-layer";
      parentEl.appendChild(this.element);
    }
    Marker.prototype.setPadding = function (padding) {
      this.$padding = padding;
    };
    Marker.prototype.setSession = function (session) {
      this.session = session;
    };
    Marker.prototype.setMarkers = function (markers) {
      this.markers = markers;
    };
    Marker.prototype.elt = function (className, css) {
      var x = this.i != -1 && this.element.childNodes[this.i];
      if (!x) {
        x = document.createElement("div");
        this.element.appendChild(x);
        this.i = -1;
      } else {
        this.i++;
      }
      x.style.cssText = css;
      x.className = className;
    };
    Marker.prototype.update = function (config) {
      if (!config) return;
      this.config = config;
      this.i = 0;
      var html;
      for (var key in this.markers) {
        var marker = this.markers[key];
        if (!marker.range) {
          marker.update(html, this, this.session, config);
          continue;
        }
        var range = marker.range.clipRows(config.firstRow, config.lastRow);
        if (range.isEmpty()) continue;
        range = range.toScreenRange(this.session);
        if (marker.renderer) {
          var top = this.$getTop(range.start.row, config);
          var left = this.$padding + range.start.column * config.characterWidth;
          marker.renderer(html, range, left, top, config);
        } else if (marker.type == "fullLine") {
          this.drawFullLineMarker(html, range, marker.clazz, config);
        } else if (marker.type == "screenLine") {
          this.drawScreenLineMarker(html, range, marker.clazz, config);
        } else if (range.isMultiLine()) {
          if (marker.type == "text")
            this.drawTextMarker(html, range, marker.clazz, config);
          else this.drawMultiLineMarker(html, range, marker.clazz, config);
        } else {
          this.drawSingleLineMarker(
            html,
            range,
            marker.clazz + " ace_start" + " ace_br15",
            config,
          );
        }
      }
      if (this.i != -1) {
        while (this.i < this.element.childElementCount)
          this.element.removeChild(this.element.lastChild);
      }
    };
    Marker.prototype.$getTop = function (row, layerConfig) {
      return (row - layerConfig.firstRowScreen) * layerConfig.lineHeight;
    };
    Marker.prototype.drawTextMarker = function (
      stringBuilder,
      range,
      clazz,
      layerConfig,
      extraStyle,
    ) {
      var session = this.session;
      var start = range.start.row;
      var end = range.end.row;
      var row = start;
      var prev = 0;
      var curr = 0;
      var next = session.getScreenLastRowColumn(row);
      var lineRange = new Range(row, range.start.column, row, curr);
      for (; row <= end; row++) {
        lineRange.start.row = lineRange.end.row = row;
        lineRange.start.column =
          row == start ? range.start.column : session.getRowWrapIndent(row);
        lineRange.end.column = next;
        prev = curr;
        curr = next;
        next =
          row + 1 < end
            ? session.getScreenLastRowColumn(row + 1)
            : row == end
              ? 0
              : range.end.column;
        this.drawSingleLineMarker(
          stringBuilder,
          lineRange,
          clazz +
            (row == start ? " ace_start" : "") +
            " ace_br" +
            getBorderClass(
              row == start || (row == start + 1 && range.start.column),
              prev < curr,
              curr > next,
              row == end,
            ),
          layerConfig,
          row == end ? 0 : 1,
          extraStyle,
        );
      }
    };
    Marker.prototype.drawMultiLineMarker = function (
      stringBuilder,
      range,
      clazz,
      config,
      extraStyle,
    ) {
      var padding = this.$padding;
      var height = config.lineHeight;
      var top = this.$getTop(range.start.row, config);
      var left = padding + range.start.column * config.characterWidth;
      extraStyle = extraStyle || "";
      if (this.session.$bidiHandler.isBidiRow(range.start.row)) {
        var range1 = range.clone();
        range1.end.row = range1.start.row;
        range1.end.column = this.session.getLine(range1.start.row).length;
        this.drawBidiSingleLineMarker(
          stringBuilder,
          range1,
          clazz + " ace_br1 ace_start",
          config,
          null,
          extraStyle,
        );
      } else {
        this.elt(
          clazz + " ace_br1 ace_start",
          "height:" +
            height +
            "px;" +
            "right:0;" +
            "top:" +
            top +
            "px;left:" +
            left +
            "px;" +
            (extraStyle || ""),
        );
      }
      if (this.session.$bidiHandler.isBidiRow(range.end.row)) {
        var range1 = range.clone();
        range1.start.row = range1.end.row;
        range1.start.column = 0;
        this.drawBidiSingleLineMarker(
          stringBuilder,
          range1,
          clazz + " ace_br12",
          config,
          null,
          extraStyle,
        );
      } else {
        top = this.$getTop(range.end.row, config);
        var width = range.end.column * config.characterWidth;
        this.elt(
          clazz + " ace_br12",
          "height:" +
            height +
            "px;" +
            "width:" +
            width +
            "px;" +
            "top:" +
            top +
            "px;" +
            "left:" +
            padding +
            "px;" +
            (extraStyle || ""),
        );
      }
      height = (range.end.row - range.start.row - 1) * config.lineHeight;
      if (height <= 0) return;
      top = this.$getTop(range.start.row + 1, config);
      var radiusClass =
        (range.start.column ? 1 : 0) | (range.end.column ? 0 : 8);
      this.elt(
        clazz + (radiusClass ? " ace_br" + radiusClass : ""),
        "height:" +
          height +
          "px;" +
          "right:0;" +
          "top:" +
          top +
          "px;" +
          "left:" +
          padding +
          "px;" +
          (extraStyle || ""),
      );
    };
    Marker.prototype.drawSingleLineMarker = function (
      stringBuilder,
      range,
      clazz,
      config,
      extraLength,
      extraStyle,
    ) {
      if (this.session.$bidiHandler.isBidiRow(range.start.row))
        return this.drawBidiSingleLineMarker(
          stringBuilder,
          range,
          clazz,
          config,
          extraLength,
          extraStyle,
        );
      var height = config.lineHeight;
      var width =
        (range.end.column + (extraLength || 0) - range.start.column) *
        config.characterWidth;
      var top = this.$getTop(range.start.row, config);
      var left = this.$padding + range.start.column * config.characterWidth;
      this.elt(
        clazz,
        "height:" +
          height +
          "px;" +
          "width:" +
          width +
          "px;" +
          "top:" +
          top +
          "px;" +
          "left:" +
          left +
          "px;" +
          (extraStyle || ""),
      );
    };
    Marker.prototype.drawBidiSingleLineMarker = function (
      stringBuilder,
      range,
      clazz,
      config,
      extraLength,
      extraStyle,
    ) {
      var height = config.lineHeight,
        top = this.$getTop(range.start.row, config),
        padding = this.$padding;
      var selections = this.session.$bidiHandler.getSelections(
        range.start.column,
        range.end.column,
      );
      selections.forEach(function (selection) {
        this.elt(
          clazz,
          "height:" +
            height +
            "px;" +
            "width:" +
            (selection.width + (extraLength || 0)) +
            "px;" +
            "top:" +
            top +
            "px;" +
            "left:" +
            (padding + selection.left) +
            "px;" +
            (extraStyle || ""),
        );
      }, this);
    };
    Marker.prototype.drawFullLineMarker = function (
      stringBuilder,
      range,
      clazz,
      config,
      extraStyle,
    ) {
      var top = this.$getTop(range.start.row, config);
      var height = config.lineHeight;
      if (range.start.row != range.end.row)
        height += this.$getTop(range.end.row, config) - top;
      this.elt(
        clazz,
        "height:" +
          height +
          "px;" +
          "top:" +
          top +
          "px;" +
          "left:0;right:0;" +
          (extraStyle || ""),
      );
    };
    Marker.prototype.drawScreenLineMarker = function (
      stringBuilder,
      range,
      clazz,
      config,
      extraStyle,
    ) {
      var top = this.$getTop(range.start.row, config);
      var height = config.lineHeight;
      this.elt(
        clazz,
        "height:" +
          height +
          "px;" +
          "top:" +
          top +
          "px;" +
          "left:0;right:0;" +
          (extraStyle || ""),
      );
    };
    return Marker;
  })();
  Marker.prototype.$padding = 0;
  function getBorderClass(tl, tr, br, bl) {
    return (tl ? 1 : 0) | (tr ? 2 : 0) | (br ? 4 : 0) | (bl ? 8 : 0);
  }
  exports.Marker = Marker;
});

define("ace/layer/text_util", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  // Tokens for which Ace just uses a simple TextNode and does not add any special className.
  var textTokens = new Set(["text", "rparen", "lparen"]);
  exports.isTextToken = function (tokenType) {
    return textTokens.has(tokenType);
  };
});

define("ace/layer/text", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/dom",
  "ace/lib/lang",
  "ace/layer/lines",
  "ace/lib/event_emitter",
  "ace/config",
  "ace/layer/text_util",
], function (require, exports, module) {
  "use strict";
  var oop = require("../lib/oop");
  var dom = require("../lib/dom");
  var lang = require("../lib/lang");
  var Lines = require("./lines").Lines;
  var EventEmitter = require("../lib/event_emitter").EventEmitter;
  var nls = require("../config").nls;
  var isTextToken = require("./text_util").isTextToken;
  var Text = /** @class */ (function () {
    function Text(parentEl) {
      this.dom = dom;
      this.element = this.dom.createElement("div");
      this.element.className = "ace_layer ace_text-layer";
      parentEl.appendChild(this.element);
      this.$updateEolChar = this.$updateEolChar.bind(this);
      this.$lines = new Lines(this.element);
    }
    Text.prototype.$updateEolChar = function () {
      var doc = this.session.doc;
      var unixMode =
        doc.getNewLineCharacter() == "\n" && doc.getNewLineMode() != "windows";
      var EOL_CHAR = unixMode ? this.EOL_CHAR_LF : this.EOL_CHAR_CRLF;
      if (this.EOL_CHAR != EOL_CHAR) {
        this.EOL_CHAR = EOL_CHAR;
        return true;
      }
    };
    Text.prototype.setPadding = function (padding) {
      this.$padding = padding;
      this.element.style.margin = "0 " + padding + "px";
    };
    Text.prototype.getLineHeight = function () {
      return this.$fontMetrics.$characterSize.height || 0;
    };
    Text.prototype.getCharacterWidth = function () {
      return this.$fontMetrics.$characterSize.width || 0;
    };
    Text.prototype.$setFontMetrics = function (measure) {
      this.$fontMetrics = measure;
      this.$fontMetrics.on(
        "changeCharacterSize",
        function (e) {
          this._signal("changeCharacterSize", e);
        }.bind(this),
      );
      this.$pollSizeChanges();
    };
    Text.prototype.checkForSizeChanges = function () {
      this.$fontMetrics.checkForSizeChanges();
    };
    Text.prototype.$pollSizeChanges = function () {
      return (this.$pollSizeChangesTimer =
        this.$fontMetrics.$pollSizeChanges());
    };
    Text.prototype.setSession = function (session) {
      this.session = session;
      if (session) this.$computeTabString();
    };
    Text.prototype.setShowInvisibles = function (showInvisibles) {
      if (this.showInvisibles == showInvisibles) return false;
      this.showInvisibles = showInvisibles;
      if (typeof showInvisibles == "string") {
        this.showSpaces = /tab/i.test(showInvisibles);
        this.showTabs = /space/i.test(showInvisibles);
        this.showEOL = /eol/i.test(showInvisibles);
      } else {
        this.showSpaces = this.showTabs = this.showEOL = showInvisibles;
      }
      this.$computeTabString();
      return true;
    };
    Text.prototype.setDisplayIndentGuides = function (display) {
      if (this.displayIndentGuides == display) return false;
      this.displayIndentGuides = display;
      this.$computeTabString();
      return true;
    };
    Text.prototype.setHighlightIndentGuides = function (highlight) {
      if (this.$highlightIndentGuides === highlight) return false;
      this.$highlightIndentGuides = highlight;
      return highlight;
    };
    Text.prototype.$computeTabString = function () {
      var tabSize = this.session.getTabSize();
      this.tabSize = tabSize;
      var tabStr = (this.$tabStrings = [0]);
      for (var i = 1; i < tabSize + 1; i++) {
        if (this.showTabs) {
          var span = this.dom.createElement("span");
          span.className = "ace_invisible ace_invisible_tab";
          span.textContent = lang.stringRepeat(this.TAB_CHAR, i);
          tabStr.push(span);
        } else {
          tabStr.push(
            this.dom.createTextNode(lang.stringRepeat(" ", i), this.element),
          );
        }
      }
      if (this.displayIndentGuides) {
        this.$indentGuideRe = /\s\S| \t|\t |\s$/;
        var className = "ace_indent-guide";
        var spaceClass = this.showSpaces
          ? " ace_invisible ace_invisible_space"
          : "";
        var spaceContent = this.showSpaces
          ? lang.stringRepeat(this.SPACE_CHAR, this.tabSize)
          : lang.stringRepeat(" ", this.tabSize);
        var tabClass = this.showTabs ? " ace_invisible ace_invisible_tab" : "";
        var tabContent = this.showTabs
          ? lang.stringRepeat(this.TAB_CHAR, this.tabSize)
          : spaceContent;
        var span = this.dom.createElement("span");
        span.className = className + spaceClass;
        span.textContent = spaceContent;
        this.$tabStrings[" "] = span;
        var span = this.dom.createElement("span");
        span.className = className + tabClass;
        span.textContent = tabContent;
        this.$tabStrings["\t"] = span;
      }
    };
    Text.prototype.updateLines = function (config, firstRow, lastRow) {
      if (
        this.config.lastRow != config.lastRow ||
        this.config.firstRow != config.firstRow
      ) {
        return this.update(config);
      }
      this.config = config;
      var first = Math.max(firstRow, config.firstRow);
      var last = Math.min(lastRow, config.lastRow);
      var lineElements = this.element.childNodes;
      var lineElementsIdx = 0;
      for (var row = config.firstRow; row < first; row++) {
        var foldLine = this.session.getFoldLine(row);
        if (foldLine) {
          if (foldLine.containsRow(first)) {
            first = foldLine.start.row;
            break;
          } else {
            row = foldLine.end.row;
          }
        }
        lineElementsIdx++;
      }
      var heightChanged = false;
      var row = first;
      var foldLine = this.session.getNextFoldLine(row);
      var foldStart = foldLine ? foldLine.start.row : Infinity;
      while (true) {
        if (row > foldStart) {
          row = foldLine.end.row + 1;
          foldLine = this.session.getNextFoldLine(row, foldLine);
          foldStart = foldLine ? foldLine.start.row : Infinity;
        }
        if (row > last) break;
        var lineElement = lineElements[lineElementsIdx++];
        if (lineElement) {
          this.dom.removeChildren(lineElement);
          this.$renderLine(
            lineElement,
            row,
            row == foldStart ? foldLine : false,
          );
          if (heightChanged)
            lineElement.style.top =
              this.$lines.computeLineTop(row, config, this.session) + "px";
          var height =
            config.lineHeight * this.session.getRowLength(row) + "px";
          if (lineElement.style.height != height) {
            heightChanged = true;
            lineElement.style.height = height;
          }
        }
        row++;
      }
      if (heightChanged) {
        while (lineElementsIdx < this.$lines.cells.length) {
          var cell = this.$lines.cells[lineElementsIdx++];
          cell.element.style.top =
            this.$lines.computeLineTop(cell.row, config, this.session) + "px";
        }
      }
    };
    Text.prototype.scrollLines = function (config) {
      var oldConfig = this.config;
      this.config = config;
      if (this.$lines.pageChanged(oldConfig, config))
        return this.update(config);
      this.$lines.moveContainer(config);
      var lastRow = config.lastRow;
      var oldLastRow = oldConfig ? oldConfig.lastRow : -1;
      if (!oldConfig || oldLastRow < config.firstRow)
        return this.update(config);
      if (lastRow < oldConfig.firstRow) return this.update(config);
      if (!oldConfig || oldConfig.lastRow < config.firstRow)
        return this.update(config);
      if (config.lastRow < oldConfig.firstRow) return this.update(config);
      if (oldConfig.firstRow < config.firstRow)
        for (
          var row = this.session.getFoldedRowCount(
            oldConfig.firstRow,
            config.firstRow - 1,
          );
          row > 0;
          row--
        )
          this.$lines.shift();
      if (oldConfig.lastRow > config.lastRow)
        for (
          var row = this.session.getFoldedRowCount(
            config.lastRow + 1,
            oldConfig.lastRow,
          );
          row > 0;
          row--
        )
          this.$lines.pop();
      if (config.firstRow < oldConfig.firstRow) {
        this.$lines.unshift(
          this.$renderLinesFragment(
            config,
            config.firstRow,
            oldConfig.firstRow - 1,
          ),
        );
      }
      if (config.lastRow > oldConfig.lastRow) {
        this.$lines.push(
          this.$renderLinesFragment(
            config,
            oldConfig.lastRow + 1,
            config.lastRow,
          ),
        );
      }
      this.$highlightIndentGuide();
    };
    Text.prototype.$renderLinesFragment = function (config, firstRow, lastRow) {
      var fragment = [];
      var row = firstRow;
      var foldLine = this.session.getNextFoldLine(row);
      var foldStart = foldLine ? foldLine.start.row : Infinity;
      while (true) {
        if (row > foldStart) {
          row = foldLine.end.row + 1;
          foldLine = this.session.getNextFoldLine(row, foldLine);
          foldStart = foldLine ? foldLine.start.row : Infinity;
        }
        if (row > lastRow) break;
        var line = this.$lines.createCell(row, config, this.session);
        var lineEl = line.element;
        this.dom.removeChildren(lineEl);
        dom.setStyle(
          lineEl.style,
          "height",
          this.$lines.computeLineHeight(row, config, this.session) + "px",
        );
        dom.setStyle(
          lineEl.style,
          "top",
          this.$lines.computeLineTop(row, config, this.session) + "px",
        );
        this.$renderLine(lineEl, row, row == foldStart ? foldLine : false);
        if (this.$useLineGroups()) {
          lineEl.className = "ace_line_group";
        } else {
          lineEl.className = "ace_line";
        }
        fragment.push(line);
        row++;
      }
      return fragment;
    };
    Text.prototype.update = function (config) {
      this.$lines.moveContainer(config);
      this.config = config;
      var firstRow = config.firstRow;
      var lastRow = config.lastRow;
      var lines = this.$lines;
      while (lines.getLength()) lines.pop();
      lines.push(this.$renderLinesFragment(config, firstRow, lastRow));
    };
    Text.prototype.$renderToken = function (
      parent,
      screenColumn,
      token,
      value,
    ) {
      var self = this;
      var re =
        /(\t)|( +)|([\x00-\x1f\x80-\xa0\xad\u1680\u180E\u2000-\u200f\u2028\u2029\u202F\u205F\uFEFF\uFFF9-\uFFFC\u2066\u2067\u2068\u202A\u202B\u202D\u202E\u202C\u2069]+)|(\u3000)|([\u1100-\u115F\u11A3-\u11A7\u11FA-\u11FF\u2329-\u232A\u2E80-\u2E99\u2E9B-\u2EF3\u2F00-\u2FD5\u2FF0-\u2FFB\u3001-\u303E\u3041-\u3096\u3099-\u30FF\u3105-\u312D\u3131-\u318E\u3190-\u31BA\u31C0-\u31E3\u31F0-\u321E\u3220-\u3247\u3250-\u32FE\u3300-\u4DBF\u4E00-\uA48C\uA490-\uA4C6\uA960-\uA97C\uAC00-\uD7A3\uD7B0-\uD7C6\uD7CB-\uD7FB\uF900-\uFAFF\uFE10-\uFE19\uFE30-\uFE52\uFE54-\uFE66\uFE68-\uFE6B\uFF01-\uFF60\uFFE0-\uFFE6]|[\uD800-\uDBFF][\uDC00-\uDFFF])/g;
      var valueFragment = this.dom.createFragment(this.element);
      var m;
      var i = 0;
      while ((m = re.exec(value))) {
        var tab = m[1];
        var simpleSpace = m[2];
        var controlCharacter = m[3];
        var cjkSpace = m[4];
        var cjk = m[5];
        if (!self.showSpaces && simpleSpace) continue;
        var before = i != m.index ? value.slice(i, m.index) : "";
        i = m.index + m[0].length;
        if (before) {
          valueFragment.appendChild(
            this.dom.createTextNode(before, this.element),
          );
        }
        if (tab) {
          var tabSize = self.session.getScreenTabSize(screenColumn + m.index);
          valueFragment.appendChild(self.$tabStrings[tabSize].cloneNode(true));
          screenColumn += tabSize - 1;
        } else if (simpleSpace) {
          if (self.showSpaces) {
            var span = this.dom.createElement("span");
            span.className = "ace_invisible ace_invisible_space";
            span.textContent = lang.stringRepeat(
              self.SPACE_CHAR,
              simpleSpace.length,
            );
            valueFragment.appendChild(span);
          } else {
            valueFragment.appendChild(
              this.dom.createTextNode(simpleSpace, this.element),
            );
          }
        } else if (controlCharacter) {
          var span = this.dom.createElement("span");
          span.className = "ace_invisible ace_invisible_space ace_invalid";
          span.textContent = lang.stringRepeat(
            self.SPACE_CHAR,
            controlCharacter.length,
          );
          valueFragment.appendChild(span);
        } else if (cjkSpace) {
          screenColumn += 1;
          var span = this.dom.createElement("span");
          span.style.width = self.config.characterWidth * 2 + "px";
          span.className = self.showSpaces
            ? "ace_cjk ace_invisible ace_invisible_space"
            : "ace_cjk";
          span.textContent = self.showSpaces ? self.SPACE_CHAR : cjkSpace;
          valueFragment.appendChild(span);
        } else if (cjk) {
          screenColumn += 1;
          var span = this.dom.createElement("span");
          span.style.width = self.config.characterWidth * 2 + "px";
          span.className = "ace_cjk";
          span.textContent = cjk;
          valueFragment.appendChild(span);
        }
      }
      valueFragment.appendChild(
        this.dom.createTextNode(i ? value.slice(i) : value, this.element),
      );
      if (!isTextToken(token.type)) {
        var classes = "ace_" + token.type.replace(/\./g, " ace_");
        var span = this.dom.createElement("span");
        if (token.type == "fold") {
          span.style.width =
            token.value.length * this.config.characterWidth + "px";
          span.setAttribute("title", nls("Unfold code"));
        }
        span.className = classes;
        span.appendChild(valueFragment);
        parent.appendChild(span);
      } else {
        parent.appendChild(valueFragment);
      }
      return screenColumn + value.length;
    };
    Text.prototype.renderIndentGuide = function (parent, value, max) {
      var cols = value.search(this.$indentGuideRe);
      if (cols <= 0 || cols >= max) return value;
      if (value[0] == " ") {
        cols -= cols % this.tabSize;
        var count = cols / this.tabSize;
        for (var i = 0; i < count; i++) {
          parent.appendChild(this.$tabStrings[" "].cloneNode(true));
        }
        this.$highlightIndentGuide();
        return value.substr(cols);
      } else if (value[0] == "\t") {
        for (var i = 0; i < cols; i++) {
          parent.appendChild(this.$tabStrings["\t"].cloneNode(true));
        }
        this.$highlightIndentGuide();
        return value.substr(cols);
      }
      this.$highlightIndentGuide();
      return value;
    };
    Text.prototype.$highlightIndentGuide = function () {
      if (!this.$highlightIndentGuides || !this.displayIndentGuides) return;
      this.$highlightIndentGuideMarker = {
        indentLevel: undefined,
        start: undefined,
        end: undefined,
        dir: undefined,
      };
      var lines = this.session.doc.$lines;
      if (!lines) return;
      var cursor = this.session.selection.getCursor();
      var initialIndent = /^\s*/.exec(this.session.doc.getLine(cursor.row))[0]
        .length;
      var elementIndentLevel = Math.floor(initialIndent / this.tabSize);
      this.$highlightIndentGuideMarker = {
        indentLevel: elementIndentLevel,
        start: cursor.row,
      };
      var bracketHighlight = this.session.$bracketHighlight;
      if (bracketHighlight) {
        var ranges = this.session.$bracketHighlight.ranges;
        for (var i = 0; i < ranges.length; i++) {
          if (cursor.row !== ranges[i].start.row) {
            this.$highlightIndentGuideMarker.end = ranges[i].start.row;
            if (cursor.row > ranges[i].start.row) {
              this.$highlightIndentGuideMarker.dir = -1;
            } else {
              this.$highlightIndentGuideMarker.dir = 1;
            }
            break;
          }
        }
      }
      if (!this.$highlightIndentGuideMarker.end) {
        if (
          lines[cursor.row] !== "" &&
          cursor.column === lines[cursor.row].length
        ) {
          this.$highlightIndentGuideMarker.dir = 1;
          for (var i = cursor.row + 1; i < lines.length; i++) {
            var line = lines[i];
            var currentIndent = /^\s*/.exec(line)[0].length;
            if (line !== "") {
              this.$highlightIndentGuideMarker.end = i;
              if (currentIndent <= initialIndent) break;
            }
          }
        }
      }
      this.$renderHighlightIndentGuide();
    };
    Text.prototype.$clearActiveIndentGuide = function () {
      var cells = this.$lines.cells;
      for (var i = 0; i < cells.length; i++) {
        var cell = cells[i];
        var childNodes = cell.element.childNodes;
        if (childNodes.length > 0) {
          for (var j = 0; j < childNodes.length; j++) {
            if (
              childNodes[j].classList &&
              childNodes[j].classList.contains("ace_indent-guide-active")
            ) {
              childNodes[j].classList.remove("ace_indent-guide-active");
              break;
            }
          }
        }
      }
    };
    Text.prototype.$setIndentGuideActive = function (cell, indentLevel) {
      var line = this.session.doc.getLine(cell.row);
      if (line !== "") {
        var childNodes = cell.element.childNodes;
        if (childNodes) {
          var node = childNodes[indentLevel - 1];
          if (
            node &&
            node.classList &&
            node.classList.contains("ace_indent-guide")
          )
            node.classList.add("ace_indent-guide-active");
        }
      }
    };
    Text.prototype.$renderHighlightIndentGuide = function () {
      if (!this.$lines) return;
      var cells = this.$lines.cells;
      this.$clearActiveIndentGuide();
      var indentLevel = this.$highlightIndentGuideMarker.indentLevel;
      if (indentLevel !== 0) {
        if (this.$highlightIndentGuideMarker.dir === 1) {
          for (var i = 0; i < cells.length; i++) {
            var cell = cells[i];
            if (
              this.$highlightIndentGuideMarker.end &&
              cell.row >= this.$highlightIndentGuideMarker.start + 1
            ) {
              if (cell.row >= this.$highlightIndentGuideMarker.end) break;
              this.$setIndentGuideActive(cell, indentLevel);
            }
          }
        } else {
          for (var i = cells.length - 1; i >= 0; i--) {
            var cell = cells[i];
            if (
              this.$highlightIndentGuideMarker.end &&
              cell.row < this.$highlightIndentGuideMarker.start
            ) {
              if (cell.row <= this.$highlightIndentGuideMarker.end) break;
              this.$setIndentGuideActive(cell, indentLevel);
            }
          }
        }
      }
    };
    Text.prototype.$createLineElement = function (parent) {
      var lineEl = this.dom.createElement("div");
      lineEl.className = "ace_line";
      lineEl.style.height = this.config.lineHeight + "px";
      return lineEl;
    };
    Text.prototype.$renderWrappedLine = function (parent, tokens, splits) {
      var chars = 0;
      var split = 0;
      var splitChars = splits[0];
      var screenColumn = 0;
      var lineEl = this.$createLineElement();
      parent.appendChild(lineEl);
      for (var i = 0; i < tokens.length; i++) {
        var token = tokens[i];
        var value = token.value;
        if (i == 0 && this.displayIndentGuides) {
          chars = value.length;
          value = this.renderIndentGuide(lineEl, value, splitChars);
          if (!value) continue;
          chars -= value.length;
        }
        if (chars + value.length < splitChars) {
          screenColumn = this.$renderToken(lineEl, screenColumn, token, value);
          chars += value.length;
        } else {
          while (chars + value.length >= splitChars) {
            screenColumn = this.$renderToken(
              lineEl,
              screenColumn,
              token,
              value.substring(0, splitChars - chars),
            );
            value = value.substring(splitChars - chars);
            chars = splitChars;
            lineEl = this.$createLineElement();
            parent.appendChild(lineEl);
            lineEl.appendChild(
              this.dom.createTextNode(
                lang.stringRepeat("\xa0", splits.indent),
                this.element,
              ),
            );
            split++;
            screenColumn = 0;
            splitChars = splits[split] || Number.MAX_VALUE;
          }
          if (value.length != 0) {
            chars += value.length;
            screenColumn = this.$renderToken(
              lineEl,
              screenColumn,
              token,
              value,
            );
          }
        }
      }
      if (splits[splits.length - 1] > this.MAX_LINE_LENGTH)
        this.$renderOverflowMessage(lineEl, screenColumn, null, "", true);
    };
    Text.prototype.$renderSimpleLine = function (parent, tokens) {
      var screenColumn = 0;
      for (var i = 0; i < tokens.length; i++) {
        var token = tokens[i];
        var value = token.value;
        if (i == 0 && this.displayIndentGuides) {
          value = this.renderIndentGuide(parent, value);
          if (!value) continue;
        }
        if (screenColumn + value.length > this.MAX_LINE_LENGTH)
          return this.$renderOverflowMessage(
            parent,
            screenColumn,
            token,
            value,
          );
        screenColumn = this.$renderToken(parent, screenColumn, token, value);
      }
    };
    Text.prototype.$renderOverflowMessage = function (
      parent,
      screenColumn,
      token,
      value,
      hide,
    ) {
      token &&
        this.$renderToken(
          parent,
          screenColumn,
          token,
          value.slice(0, this.MAX_LINE_LENGTH - screenColumn),
        );
      var overflowEl = this.dom.createElement("span");
      overflowEl.className = "ace_inline_button ace_keyword ace_toggle_wrap";
      overflowEl.textContent = hide ? "<hide>" : "<click to see more...>";
      parent.appendChild(overflowEl);
    };
    Text.prototype.$renderLine = function (parent, row, foldLine) {
      if (!foldLine && foldLine != false)
        foldLine = this.session.getFoldLine(row);
      if (foldLine) var tokens = this.$getFoldLineTokens(row, foldLine);
      else var tokens = this.session.getTokens(row);
      var lastLineEl = parent;
      if (tokens.length) {
        var splits = this.session.getRowSplitData(row);
        if (splits && splits.length) {
          this.$renderWrappedLine(parent, tokens, splits);
          var lastLineEl = parent.lastChild;
        } else {
          var lastLineEl = parent;
          if (this.$useLineGroups()) {
            lastLineEl = this.$createLineElement();
            parent.appendChild(lastLineEl);
          }
          this.$renderSimpleLine(lastLineEl, tokens);
        }
      } else if (this.$useLineGroups()) {
        lastLineEl = this.$createLineElement();
        parent.appendChild(lastLineEl);
      }
      if (this.showEOL && lastLineEl) {
        if (foldLine) row = foldLine.end.row;
        var invisibleEl = this.dom.createElement("span");
        invisibleEl.className = "ace_invisible ace_invisible_eol";
        invisibleEl.textContent =
          row == this.session.getLength() - 1 ? this.EOF_CHAR : this.EOL_CHAR;
        lastLineEl.appendChild(invisibleEl);
      }
    };
    Text.prototype.$getFoldLineTokens = function (row, foldLine) {
      var session = this.session;
      var renderTokens = [];
      function addTokens(tokens, from, to) {
        var idx = 0,
          col = 0;
        while (col + tokens[idx].value.length < from) {
          col += tokens[idx].value.length;
          idx++;
          if (idx == tokens.length) return;
        }
        if (col != from) {
          var value = tokens[idx].value.substring(from - col);
          if (value.length > to - from) value = value.substring(0, to - from);
          renderTokens.push({
            type: tokens[idx].type,
            value: value,
          });
          col = from + value.length;
          idx += 1;
        }
        while (col < to && idx < tokens.length) {
          var value = tokens[idx].value;
          if (value.length + col > to) {
            renderTokens.push({
              type: tokens[idx].type,
              value: value.substring(0, to - col),
            });
          } else renderTokens.push(tokens[idx]);
          col += value.length;
          idx += 1;
        }
      }
      var tokens = session.getTokens(row);
      foldLine.walk(
        function (placeholder, row, column, lastColumn, isNewRow) {
          if (placeholder != null) {
            renderTokens.push({
              type: "fold",
              value: placeholder,
            });
          } else {
            if (isNewRow) tokens = session.getTokens(row);
            if (tokens.length) addTokens(tokens, lastColumn, column);
          }
        },
        foldLine.end.row,
        this.session.getLine(foldLine.end.row).length,
      );
      return renderTokens;
    };
    Text.prototype.$useLineGroups = function () {
      return this.session.getUseWrapMode();
    };
    return Text;
  })();
  Text.prototype.EOF_CHAR = "\xB6";
  Text.prototype.EOL_CHAR_LF = "\xAC";
  Text.prototype.EOL_CHAR_CRLF = "\xa4";
  Text.prototype.EOL_CHAR = Text.prototype.EOL_CHAR_LF;
  Text.prototype.TAB_CHAR = "\u2014"; //"\u21E5";
  Text.prototype.SPACE_CHAR = "\xB7";
  Text.prototype.$padding = 0;
  Text.prototype.MAX_LINE_LENGTH = 10000;
  Text.prototype.showInvisibles = false;
  Text.prototype.showSpaces = false;
  Text.prototype.showTabs = false;
  Text.prototype.showEOL = false;
  Text.prototype.displayIndentGuides = true;
  Text.prototype.$highlightIndentGuides = true;
  Text.prototype.$tabStrings = [];
  Text.prototype.destroy = {};
  Text.prototype.onChangeTabSize = Text.prototype.$computeTabString;
  oop.implement(Text.prototype, EventEmitter);
  exports.Text = Text;
});

define("ace/layer/cursor", [
  "require",
  "exports",
  "module",
  "ace/lib/dom",
], function (require, exports, module) {
  "use strict";
  var dom = require("../lib/dom");
  var Cursor = /** @class */ (function () {
    function Cursor(parentEl) {
      this.element = dom.createElement("div");
      this.element.className = "ace_layer ace_cursor-layer";
      parentEl.appendChild(this.element);
      this.isVisible = false;
      this.isBlinking = true;
      this.blinkInterval = 1000;
      this.smoothBlinking = false;
      this.cursors = [];
      this.cursor = this.addCursor();
      dom.addCssClass(this.element, "ace_hidden-cursors");
      this.$updateCursors = this.$updateOpacity.bind(this);
    }
    Cursor.prototype.$updateOpacity = function (val) {
      var cursors = this.cursors;
      for (var i = cursors.length; i--; )
        dom.setStyle(cursors[i].style, "opacity", val ? "" : "0");
    };
    Cursor.prototype.$startCssAnimation = function () {
      var cursors = this.cursors;
      for (var i = cursors.length; i--; )
        cursors[i].style.animationDuration = this.blinkInterval + "ms";
      this.$isAnimating = true;
      setTimeout(
        function () {
          if (this.$isAnimating) {
            dom.addCssClass(this.element, "ace_animate-blinking");
          }
        }.bind(this),
      );
    };
    Cursor.prototype.$stopCssAnimation = function () {
      this.$isAnimating = false;
      dom.removeCssClass(this.element, "ace_animate-blinking");
    };
    Cursor.prototype.setPadding = function (padding) {
      this.$padding = padding;
    };
    Cursor.prototype.setSession = function (session) {
      this.session = session;
    };
    Cursor.prototype.setBlinking = function (blinking) {
      if (blinking != this.isBlinking) {
        this.isBlinking = blinking;
        this.restartTimer();
      }
    };
    Cursor.prototype.setBlinkInterval = function (blinkInterval) {
      if (blinkInterval != this.blinkInterval) {
        this.blinkInterval = blinkInterval;
        this.restartTimer();
      }
    };
    Cursor.prototype.setSmoothBlinking = function (smoothBlinking) {
      if (smoothBlinking != this.smoothBlinking) {
        this.smoothBlinking = smoothBlinking;
        dom.setCssClass(this.element, "ace_smooth-blinking", smoothBlinking);
        this.$updateCursors(true);
        this.restartTimer();
      }
    };
    Cursor.prototype.addCursor = function () {
      var el = dom.createElement("div");
      el.className = "ace_cursor";
      this.element.appendChild(el);
      this.cursors.push(el);
      return el;
    };
    Cursor.prototype.removeCursor = function () {
      if (this.cursors.length > 1) {
        var el = this.cursors.pop();
        el.parentNode.removeChild(el);
        return el;
      }
    };
    Cursor.prototype.hideCursor = function () {
      this.isVisible = false;
      dom.addCssClass(this.element, "ace_hidden-cursors");
      this.restartTimer();
    };
    Cursor.prototype.showCursor = function () {
      this.isVisible = true;
      dom.removeCssClass(this.element, "ace_hidden-cursors");
      this.restartTimer();
    };
    Cursor.prototype.restartTimer = function () {
      var update = this.$updateCursors;
      clearInterval(this.intervalId);
      clearTimeout(this.timeoutId);
      this.$stopCssAnimation();
      if (this.smoothBlinking) {
        this.$isSmoothBlinking = false;
        dom.removeCssClass(this.element, "ace_smooth-blinking");
      }
      update(true);
      if (!this.isBlinking || !this.blinkInterval || !this.isVisible) {
        this.$stopCssAnimation();
        return;
      }
      if (this.smoothBlinking) {
        this.$isSmoothBlinking = true;
        setTimeout(
          function () {
            if (this.$isSmoothBlinking) {
              dom.addCssClass(this.element, "ace_smooth-blinking");
            }
          }.bind(this),
        );
      }
      if (dom.HAS_CSS_ANIMATION) {
        this.$startCssAnimation();
      } else {
        var blink = /**@this{Cursor}*/ function () {
          this.timeoutId = setTimeout(function () {
            update(false);
          }, 0.6 * this.blinkInterval);
        }.bind(this);
        this.intervalId = setInterval(function () {
          update(true);
          blink();
        }, this.blinkInterval);
        blink();
      }
    };
    Cursor.prototype.getPixelPosition = function (position, onScreen) {
      if (!this.config || !this.session) return { left: 0, top: 0 };
      if (!position) position = this.session.selection.getCursor();
      var pos = this.session.documentToScreenPosition(position);
      var cursorLeft =
        this.$padding +
        (this.session.$bidiHandler.isBidiRow(pos.row, position.row)
          ? this.session.$bidiHandler.getPosLeft(pos.column)
          : pos.column * this.config.characterWidth);
      var cursorTop =
        (pos.row - (onScreen ? this.config.firstRowScreen : 0)) *
        this.config.lineHeight;
      return { left: cursorLeft, top: cursorTop };
    };
    Cursor.prototype.isCursorInView = function (pixelPos, config) {
      return pixelPos.top >= 0 && pixelPos.top < config.maxHeight;
    };
    Cursor.prototype.update = function (config) {
      this.config = config;
      var selections = this.session.$selectionMarkers;
      var i = 0,
        cursorIndex = 0;
      if (selections === undefined || selections.length === 0) {
        selections = [{ cursor: null }];
      }
      for (var i = 0, n = selections.length; i < n; i++) {
        var pixelPos = this.getPixelPosition(selections[i].cursor, true);
        if (
          (pixelPos.top > config.height + config.offset || pixelPos.top < 0) &&
          i > 1
        ) {
          continue;
        }
        var element = this.cursors[cursorIndex++] || this.addCursor();
        var style = element.style;
        if (!this.drawCursor) {
          if (!this.isCursorInView(pixelPos, config)) {
            dom.setStyle(style, "display", "none");
          } else {
            dom.setStyle(style, "display", "block");
            dom.translate(element, pixelPos.left, pixelPos.top);
            dom.setStyle(
              style,
              "width",
              Math.round(config.characterWidth) + "px",
            );
            dom.setStyle(style, "height", config.lineHeight + "px");
          }
        } else {
          this.drawCursor(
            element,
            pixelPos,
            config,
            selections[i],
            this.session,
          );
        }
      }
      while (this.cursors.length > cursorIndex) this.removeCursor();
      var overwrite = this.session.getOverwrite();
      this.$setOverwrite(overwrite);
      this.$pixelPos = pixelPos;
      this.restartTimer();
    };
    Cursor.prototype.$setOverwrite = function (overwrite) {
      if (overwrite != this.overwrite) {
        this.overwrite = overwrite;
        if (overwrite) dom.addCssClass(this.element, "ace_overwrite-cursors");
        else dom.removeCssClass(this.element, "ace_overwrite-cursors");
      }
    };
    Cursor.prototype.destroy = function () {
      clearInterval(this.intervalId);
      clearTimeout(this.timeoutId);
    };
    return Cursor;
  })();
  Cursor.prototype.$padding = 0;
  Cursor.prototype.drawCursor = null;
  exports.Cursor = Cursor;
});

define("ace/scrollbar", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/dom",
  "ace/lib/event",
  "ace/lib/event_emitter",
], function (require, exports, module) {
  "use strict";
  var __extends =
    (this && this.__extends) ||
    (function () {
      var extendStatics = function (d, b) {
        extendStatics =
          Object.setPrototypeOf ||
          ({ __proto__: [] } instanceof Array &&
            function (d, b) {
              d.__proto__ = b;
            }) ||
          function (d, b) {
            for (var p in b)
              if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p];
          };
        return extendStatics(d, b);
      };
      return function (d, b) {
        if (typeof b !== "function" && b !== null)
          throw new TypeError(
            "Class extends value " +
              String(b) +
              " is not a constructor or null",
          );
        extendStatics(d, b);
        function __() {
          this.constructor = d;
        }
        d.prototype =
          b === null
            ? Object.create(b)
            : ((__.prototype = b.prototype), new __());
      };
    })();
  var oop = require("./lib/oop");
  var dom = require("./lib/dom");
  var event = require("./lib/event");
  var EventEmitter = require("./lib/event_emitter").EventEmitter;
  var MAX_SCROLL_H = 0x8000;
  var Scrollbar = /** @class */ (function () {
    function Scrollbar(parent, classSuffix) {
      this.element = dom.createElement("div");
      this.element.className = "ace_scrollbar ace_scrollbar" + classSuffix;
      this.inner = dom.createElement("div");
      this.inner.className = "ace_scrollbar-inner";
      this.inner.textContent = "\xa0";
      this.element.appendChild(this.inner);
      parent.appendChild(this.element);
      this.setVisible(false);
      this.skipEvent = false;
      event.addListener(this.element, "scroll", this.onScroll.bind(this));
      event.addListener(this.element, "mousedown", event.preventDefault);
    }
    Scrollbar.prototype.setVisible = function (isVisible) {
      this.element.style.display = isVisible ? "" : "none";
      this.isVisible = isVisible;
      this.coeff = 1;
    };
    return Scrollbar;
  })();
  oop.implement(Scrollbar.prototype, EventEmitter);
  var VScrollBar = /** @class */ (function (_super) {
    __extends(VScrollBar, _super);
    function VScrollBar(parent, renderer) {
      var _this = _super.call(this, parent, "-v") || this;
      _this.scrollTop = 0;
      _this.scrollHeight = 0;
      renderer.$scrollbarWidth = _this.width = dom.scrollbarWidth(
        parent.ownerDocument,
      );
      _this.inner.style.width = _this.element.style.width =
        (_this.width || 15) + 5 + "px";
      _this.$minWidth = 0;
      return _this;
    }
    VScrollBar.prototype.onScroll = function () {
      if (!this.skipEvent) {
        this.scrollTop = this.element.scrollTop;
        if (this.coeff != 1) {
          var h = this.element.clientHeight / this.scrollHeight;
          this.scrollTop = (this.scrollTop * (1 - h)) / (this.coeff - h);
        }
        this._emit("scroll", { data: this.scrollTop });
      }
      this.skipEvent = false;
    };
    VScrollBar.prototype.getWidth = function () {
      return Math.max(this.isVisible ? this.width : 0, this.$minWidth || 0);
    };
    VScrollBar.prototype.setHeight = function (height) {
      this.element.style.height = height + "px";
    };
    VScrollBar.prototype.setScrollHeight = function (height) {
      this.scrollHeight = height;
      if (height > MAX_SCROLL_H) {
        this.coeff = MAX_SCROLL_H / height;
        height = MAX_SCROLL_H;
      } else if (this.coeff != 1) {
        this.coeff = 1;
      }
      this.inner.style.height = height + "px";
    };
    VScrollBar.prototype.setScrollTop = function (scrollTop) {
      if (this.scrollTop != scrollTop) {
        this.skipEvent = true;
        this.scrollTop = scrollTop;
        this.element.scrollTop = scrollTop * this.coeff;
      }
    };
    return VScrollBar;
  })(Scrollbar);
  VScrollBar.prototype.setInnerHeight = VScrollBar.prototype.setScrollHeight;
  var HScrollBar = /** @class */ (function (_super) {
    __extends(HScrollBar, _super);
    function HScrollBar(parent, renderer) {
      var _this = _super.call(this, parent, "-h") || this;
      _this.scrollLeft = 0;
      _this.height = renderer.$scrollbarWidth;
      _this.inner.style.height = _this.element.style.height =
        (_this.height || 15) + 5 + "px";
      return _this;
    }
    HScrollBar.prototype.onScroll = function () {
      if (!this.skipEvent) {
        this.scrollLeft = this.element.scrollLeft;
        this._emit("scroll", { data: this.scrollLeft });
      }
      this.skipEvent = false;
    };
    HScrollBar.prototype.getHeight = function () {
      return this.isVisible ? this.height : 0;
    };
    HScrollBar.prototype.setWidth = function (width) {
      this.element.style.width = width + "px";
    };
    HScrollBar.prototype.setInnerWidth = function (width) {
      this.inner.style.width = width + "px";
    };
    HScrollBar.prototype.setScrollWidth = function (width) {
      this.inner.style.width = width + "px";
    };
    HScrollBar.prototype.setScrollLeft = function (scrollLeft) {
      if (this.scrollLeft != scrollLeft) {
        this.skipEvent = true;
        this.scrollLeft = this.element.scrollLeft = scrollLeft;
      }
    };
    return HScrollBar;
  })(Scrollbar);
  exports.ScrollBar = VScrollBar; // backward compatibility
  exports.ScrollBarV = VScrollBar; // backward compatibility
  exports.ScrollBarH = HScrollBar; // backward compatibility
  exports.VScrollBar = VScrollBar;
  exports.HScrollBar = HScrollBar;
});

define("ace/scrollbar_custom", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/dom",
  "ace/lib/event",
  "ace/lib/event_emitter",
], function (require, exports, module) {
  "use strict";
  var __extends =
    (this && this.__extends) ||
    (function () {
      var extendStatics = function (d, b) {
        extendStatics =
          Object.setPrototypeOf ||
          ({ __proto__: [] } instanceof Array &&
            function (d, b) {
              d.__proto__ = b;
            }) ||
          function (d, b) {
            for (var p in b)
              if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p];
          };
        return extendStatics(d, b);
      };
      return function (d, b) {
        if (typeof b !== "function" && b !== null)
          throw new TypeError(
            "Class extends value " +
              String(b) +
              " is not a constructor or null",
          );
        extendStatics(d, b);
        function __() {
          this.constructor = d;
        }
        d.prototype =
          b === null
            ? Object.create(b)
            : ((__.prototype = b.prototype), new __());
      };
    })();
  var oop = require("./lib/oop");
  var dom = require("./lib/dom");
  var event = require("./lib/event");
  var EventEmitter = require("./lib/event_emitter").EventEmitter;
  dom.importCssString(
    ".ace_editor>.ace_sb-v div, .ace_editor>.ace_sb-h div{\n  position: absolute;\n  background: rgba(128, 128, 128, 0.6);\n  -moz-box-sizing: border-box;\n  box-sizing: border-box;\n  border: 1px solid #bbb;\n  border-radius: 2px;\n  z-index: 8;\n}\n.ace_editor>.ace_sb-v, .ace_editor>.ace_sb-h {\n  position: absolute;\n  z-index: 6;\n  background: none;\n  overflow: hidden!important;\n}\n.ace_editor>.ace_sb-v {\n  z-index: 6;\n  right: 0;\n  top: 0;\n  width: 12px;\n}\n.ace_editor>.ace_sb-v div {\n  z-index: 8;\n  right: 0;\n  width: 100%;\n}\n.ace_editor>.ace_sb-h {\n  bottom: 0;\n  left: 0;\n  height: 12px;\n}\n.ace_editor>.ace_sb-h div {\n  bottom: 0;\n  height: 100%;\n}\n.ace_editor>.ace_sb_grabbed {\n  z-index: 8;\n  background: #000;\n}",
    "ace_scrollbar.css",
    false,
  );
  var ScrollBar = /** @class */ (function () {
    function ScrollBar(parent, classSuffix) {
      this.element = dom.createElement("div");
      this.element.className = "ace_sb" + classSuffix;
      this.inner = dom.createElement("div");
      this.inner.className = "";
      this.element.appendChild(this.inner);
      this.VScrollWidth = 12;
      this.HScrollHeight = 12;
      parent.appendChild(this.element);
      this.setVisible(false);
      this.skipEvent = false;
      event.addMultiMouseDownListener(
        this.element,
        [500, 300, 300],
        this,
        "onMouseDown",
      );
    }
    ScrollBar.prototype.setVisible = function (isVisible) {
      this.element.style.display = isVisible ? "" : "none";
      this.isVisible = isVisible;
      this.coeff = 1;
    };
    return ScrollBar;
  })();
  oop.implement(ScrollBar.prototype, EventEmitter);
  var VScrollBar = /** @class */ (function (_super) {
    __extends(VScrollBar, _super);
    function VScrollBar(parent, renderer) {
      var _this = _super.call(this, parent, "-v") || this;
      _this.scrollTop = 0;
      _this.scrollHeight = 0;
      _this.parent = parent;
      _this.width = _this.VScrollWidth;
      _this.renderer = renderer;
      _this.inner.style.width = _this.element.style.width =
        (_this.width || 15) + "px";
      _this.$minWidth = 0;
      return _this;
    }
    VScrollBar.prototype.onMouseDown = function (eType, e) {
      if (eType !== "mousedown") return;
      if (event.getButton(e) !== 0 || e.detail === 2) {
        return;
      }
      if (e.target === this.inner) {
        var self = this;
        var mousePageY = e.clientY;
        var onMouseMove = function (e) {
          mousePageY = e.clientY;
        };
        var onMouseUp = function () {
          clearInterval(timerId);
        };
        var startY = e.clientY;
        var startTop = this.thumbTop;
        var onScrollInterval = function () {
          if (mousePageY === undefined) return;
          var scrollTop = self.scrollTopFromThumbTop(
            startTop + mousePageY - startY,
          );
          if (scrollTop === self.scrollTop) return;
          self._emit("scroll", { data: scrollTop });
        };
        event.capture(this.inner, onMouseMove, onMouseUp);
        var timerId = setInterval(onScrollInterval, 20);
        return event.preventDefault(e);
      }
      var top =
        e.clientY -
        this.element.getBoundingClientRect().top -
        this.thumbHeight / 2;
      this._emit("scroll", { data: this.scrollTopFromThumbTop(top) });
      return event.preventDefault(e);
    };
    VScrollBar.prototype.getHeight = function () {
      return this.height;
    };
    VScrollBar.prototype.scrollTopFromThumbTop = function (thumbTop) {
      var scrollTop =
        (thumbTop * (this.pageHeight - this.viewHeight)) /
        (this.slideHeight - this.thumbHeight);
      scrollTop = scrollTop >> 0;
      if (scrollTop < 0) {
        scrollTop = 0;
      } else if (scrollTop > this.pageHeight - this.viewHeight) {
        scrollTop = this.pageHeight - this.viewHeight;
      }
      return scrollTop;
    };
    VScrollBar.prototype.getWidth = function () {
      return Math.max(this.isVisible ? this.width : 0, this.$minWidth || 0);
    };
    VScrollBar.prototype.setHeight = function (height) {
      this.height = Math.max(0, height);
      this.slideHeight = this.height;
      this.viewHeight = this.height;
      this.setScrollHeight(this.pageHeight, true);
    };
    VScrollBar.prototype.setScrollHeight = function (height, force) {
      if (this.pageHeight === height && !force) return;
      this.pageHeight = height;
      this.thumbHeight = (this.slideHeight * this.viewHeight) / this.pageHeight;
      if (this.thumbHeight > this.slideHeight)
        this.thumbHeight = this.slideHeight;
      if (this.thumbHeight < 15) this.thumbHeight = 15;
      this.inner.style.height = this.thumbHeight + "px";
      if (this.scrollTop > this.pageHeight - this.viewHeight) {
        this.scrollTop = this.pageHeight - this.viewHeight;
        if (this.scrollTop < 0) this.scrollTop = 0;
        this._emit("scroll", { data: this.scrollTop });
      }
    };
    VScrollBar.prototype.setScrollTop = function (scrollTop) {
      this.scrollTop = scrollTop;
      if (scrollTop < 0) scrollTop = 0;
      this.thumbTop =
        (scrollTop * (this.slideHeight - this.thumbHeight)) /
        (this.pageHeight - this.viewHeight);
      this.inner.style.top = this.thumbTop + "px";
    };
    return VScrollBar;
  })(ScrollBar);
  VScrollBar.prototype.setInnerHeight = VScrollBar.prototype.setScrollHeight;
  var HScrollBar = /** @class */ (function (_super) {
    __extends(HScrollBar, _super);
    function HScrollBar(parent, renderer) {
      var _this = _super.call(this, parent, "-h") || this;
      _this.scrollLeft = 0;
      _this.scrollWidth = 0;
      _this.height = _this.HScrollHeight;
      _this.inner.style.height = _this.element.style.height =
        (_this.height || 12) + "px";
      _this.renderer = renderer;
      return _this;
    }
    HScrollBar.prototype.onMouseDown = function (eType, e) {
      if (eType !== "mousedown") return;
      if (event.getButton(e) !== 0 || e.detail === 2) {
        return;
      }
      if (e.target === this.inner) {
        var self = this;
        var mousePageX = e.clientX;
        var onMouseMove = function (e) {
          mousePageX = e.clientX;
        };
        var onMouseUp = function () {
          clearInterval(timerId);
        };
        var startX = e.clientX;
        var startLeft = this.thumbLeft;
        var onScrollInterval = function () {
          if (mousePageX === undefined) return;
          var scrollLeft = self.scrollLeftFromThumbLeft(
            startLeft + mousePageX - startX,
          );
          if (scrollLeft === self.scrollLeft) return;
          self._emit("scroll", { data: scrollLeft });
        };
        event.capture(this.inner, onMouseMove, onMouseUp);
        var timerId = setInterval(onScrollInterval, 20);
        return event.preventDefault(e);
      }
      var left =
        e.clientX -
        this.element.getBoundingClientRect().left -
        this.thumbWidth / 2;
      this._emit("scroll", { data: this.scrollLeftFromThumbLeft(left) });
      return event.preventDefault(e);
    };
    HScrollBar.prototype.getHeight = function () {
      return this.isVisible ? this.height : 0;
    };
    HScrollBar.prototype.scrollLeftFromThumbLeft = function (thumbLeft) {
      var scrollLeft =
        (thumbLeft * (this.pageWidth - this.viewWidth)) /
        (this.slideWidth - this.thumbWidth);
      scrollLeft = scrollLeft >> 0;
      if (scrollLeft < 0) {
        scrollLeft = 0;
      } else if (scrollLeft > this.pageWidth - this.viewWidth) {
        scrollLeft = this.pageWidth - this.viewWidth;
      }
      return scrollLeft;
    };
    HScrollBar.prototype.setWidth = function (width) {
      this.width = Math.max(0, width);
      this.element.style.width = this.width + "px";
      this.slideWidth = this.width;
      this.viewWidth = this.width;
      this.setScrollWidth(this.pageWidth, true);
    };
    HScrollBar.prototype.setScrollWidth = function (width, force) {
      if (this.pageWidth === width && !force) return;
      this.pageWidth = width;
      this.thumbWidth = (this.slideWidth * this.viewWidth) / this.pageWidth;
      if (this.thumbWidth > this.slideWidth) this.thumbWidth = this.slideWidth;
      if (this.thumbWidth < 15) this.thumbWidth = 15;
      this.inner.style.width = this.thumbWidth + "px";
      if (this.scrollLeft > this.pageWidth - this.viewWidth) {
        this.scrollLeft = this.pageWidth - this.viewWidth;
        if (this.scrollLeft < 0) this.scrollLeft = 0;
        this._emit("scroll", { data: this.scrollLeft });
      }
    };
    HScrollBar.prototype.setScrollLeft = function (scrollLeft) {
      this.scrollLeft = scrollLeft;
      if (scrollLeft < 0) scrollLeft = 0;
      this.thumbLeft =
        (scrollLeft * (this.slideWidth - this.thumbWidth)) /
        (this.pageWidth - this.viewWidth);
      this.inner.style.left = this.thumbLeft + "px";
    };
    return HScrollBar;
  })(ScrollBar);
  HScrollBar.prototype.setInnerWidth = HScrollBar.prototype.setScrollWidth;
  exports.ScrollBar = VScrollBar; // backward compatibility
  exports.ScrollBarV = VScrollBar; // backward compatibility
  exports.ScrollBarH = HScrollBar; // backward compatibility
  exports.VScrollBar = VScrollBar;
  exports.HScrollBar = HScrollBar;
});

define("ace/renderloop", [
  "require",
  "exports",
  "module",
  "ace/lib/event",
], function (require, exports, module) {
  "use strict";
  var event = require("./lib/event");
  var RenderLoop = /** @class */ (function () {
    function RenderLoop(onRender, win) {
      this.onRender = onRender;
      this.pending = false;
      this.changes = 0;
      this.$recursionLimit = 2;
      this.window = win || window;
      var _self = this;
      this._flush = function (ts) {
        _self.pending = false;
        var changes = _self.changes;
        if (changes) {
          event.blockIdle(100);
          _self.changes = 0;
          _self.onRender(changes);
        }
        if (_self.changes) {
          if (_self.$recursionLimit-- < 0) return;
          _self.schedule();
        } else {
          _self.$recursionLimit = 2;
        }
      };
    }
    RenderLoop.prototype.schedule = function (change) {
      this.changes = this.changes | change;
      if (this.changes && !this.pending) {
        event.nextFrame(this._flush);
        this.pending = true;
      }
    };
    RenderLoop.prototype.clear = function (change) {
      var changes = this.changes;
      this.changes = 0;
      return changes;
    };
    return RenderLoop;
  })();
  exports.RenderLoop = RenderLoop;
});

define("ace/layer/font_metrics", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/dom",
  "ace/lib/lang",
  "ace/lib/event",
  "ace/lib/useragent",
  "ace/lib/event_emitter",
], function (require, exports, module) {
  var oop = require("../lib/oop");
  var dom = require("../lib/dom");
  var lang = require("../lib/lang");
  var event = require("../lib/event");
  var useragent = require("../lib/useragent");
  var EventEmitter = require("../lib/event_emitter").EventEmitter;
  var CHAR_COUNT = 512;
  var USE_OBSERVER = typeof ResizeObserver == "function";
  var L = 200;
  var FontMetrics = /** @class */ (function () {
    function FontMetrics(parentEl) {
      this.el = dom.createElement("div");
      this.$setMeasureNodeStyles(this.el.style, true);
      this.$main = dom.createElement("div");
      this.$setMeasureNodeStyles(this.$main.style);
      this.$measureNode = dom.createElement("div");
      this.$setMeasureNodeStyles(this.$measureNode.style);
      this.el.appendChild(this.$main);
      this.el.appendChild(this.$measureNode);
      parentEl.appendChild(this.el);
      this.$measureNode.textContent = lang.stringRepeat("X", CHAR_COUNT);
      this.$characterSize = { width: 0, height: 0 };
      if (USE_OBSERVER) this.$addObserver();
      else this.checkForSizeChanges();
    }
    FontMetrics.prototype.$setMeasureNodeStyles = function (style, isRoot) {
      style.width = style.height = "auto";
      style.left = style.top = "0px";
      style.visibility = "hidden";
      style.position = "absolute";
      style.whiteSpace = "pre";
      if (useragent.isIE < 8) {
        style["font-family"] = "inherit";
      } else {
        style.font = "inherit";
      }
      style.overflow = isRoot ? "hidden" : "visible";
    };
    FontMetrics.prototype.checkForSizeChanges = function (size) {
      if (size === undefined) size = this.$measureSizes();
      if (
        size &&
        (this.$characterSize.width !== size.width ||
          this.$characterSize.height !== size.height)
      ) {
        this.$measureNode.style.fontWeight = "bold";
        var boldSize = this.$measureSizes();
        this.$measureNode.style.fontWeight = "";
        this.$characterSize = size;
        this.charSizes = Object.create(null);
        this.allowBoldFonts =
          boldSize &&
          boldSize.width === size.width &&
          boldSize.height === size.height;
        this._emit("changeCharacterSize", { data: size });
      }
    };
    FontMetrics.prototype.$addObserver = function () {
      var self = this;
      this.$observer = new window.ResizeObserver(function (e) {
        self.checkForSizeChanges();
      });
      this.$observer.observe(this.$measureNode);
    };
    FontMetrics.prototype.$pollSizeChanges = function () {
      if (this.$pollSizeChangesTimer || this.$observer)
        return this.$pollSizeChangesTimer;
      var self = this;
      return (this.$pollSizeChangesTimer = event.onIdle(function cb() {
        self.checkForSizeChanges();
        event.onIdle(cb, 500);
      }, 500));
    };
    FontMetrics.prototype.setPolling = function (val) {
      if (val) {
        this.$pollSizeChanges();
      } else if (this.$pollSizeChangesTimer) {
        clearInterval(this.$pollSizeChangesTimer);
        this.$pollSizeChangesTimer = 0;
      }
    };
    FontMetrics.prototype.$measureSizes = function (node) {
      var size = {
        height: (node || this.$measureNode).clientHeight,
        width: (node || this.$measureNode).clientWidth / CHAR_COUNT,
      };
      if (size.width === 0 || size.height === 0) return null;
      return size;
    };
    FontMetrics.prototype.$measureCharWidth = function (ch) {
      this.$main.textContent = lang.stringRepeat(ch, CHAR_COUNT);
      var rect = this.$main.getBoundingClientRect();
      return rect.width / CHAR_COUNT;
    };
    FontMetrics.prototype.getCharacterWidth = function (ch) {
      var w = this.charSizes[ch];
      if (w === undefined) {
        w = this.charSizes[ch] =
          this.$measureCharWidth(ch) / this.$characterSize.width;
      }
      return w;
    };
    FontMetrics.prototype.destroy = function () {
      clearInterval(this.$pollSizeChangesTimer);
      if (this.$observer) this.$observer.disconnect();
      if (this.el && this.el.parentNode)
        this.el.parentNode.removeChild(this.el);
    };
    FontMetrics.prototype.$getZoom = function (element) {
      if (!element || !element.parentElement) return 1;
      return (
        (window.getComputedStyle(element)["zoom"] || 1) *
        this.$getZoom(element.parentElement)
      );
    };
    FontMetrics.prototype.$initTransformMeasureNodes = function () {
      var t = function (t, l) {
        return [
          "div",
          {
            style: "position: absolute;top:" + t + "px;left:" + l + "px;",
          },
        ];
      };
      this.els = dom.buildDom([t(0, 0), t(L, 0), t(0, L), t(L, L)], this.el);
    };
    FontMetrics.prototype.transformCoordinates = function (clientPos, elPos) {
      if (clientPos) {
        var zoom = this.$getZoom(this.el);
        clientPos = mul(1 / zoom, clientPos);
      }
      function solve(l1, l2, r) {
        var det = l1[1] * l2[0] - l1[0] * l2[1];
        return [
          (-l2[1] * r[0] + l2[0] * r[1]) / det,
          (+l1[1] * r[0] - l1[0] * r[1]) / det,
        ];
      }
      function sub(a, b) {
        return [a[0] - b[0], a[1] - b[1]];
      }
      function add(a, b) {
        return [a[0] + b[0], a[1] + b[1]];
      }
      function mul(a, b) {
        return [a * b[0], a * b[1]];
      }
      if (!this.els) this.$initTransformMeasureNodes();
      function p(el) {
        var r = el.getBoundingClientRect();
        return [r.left, r.top];
      }
      var a = p(this.els[0]);
      var b = p(this.els[1]);
      var c = p(this.els[2]);
      var d = p(this.els[3]);
      var h = solve(sub(d, b), sub(d, c), sub(add(b, c), add(d, a)));
      var m1 = mul(1 + h[0], sub(b, a));
      var m2 = mul(1 + h[1], sub(c, a));
      if (elPos) {
        var x = elPos;
        var k = (h[0] * x[0]) / L + (h[1] * x[1]) / L + 1;
        var ut = add(mul(x[0], m1), mul(x[1], m2));
        return add(mul(1 / k / L, ut), a);
      }
      var u = sub(clientPos, a);
      var f = solve(sub(m1, mul(h[0], u)), sub(m2, mul(h[1], u)), u);
      return mul(L, f);
    };
    return FontMetrics;
  })();
  FontMetrics.prototype.$characterSize = { width: 0, height: 0 };
  oop.implement(FontMetrics.prototype, EventEmitter);
  exports.FontMetrics = FontMetrics;
});

define("ace/css/editor-css", ["require", "exports", "module"], function (
  require,
  exports,
  module,
) {
  /*
    styles = []
    for (var i = 1; i < 16; i++) {
        styles.push(".ace_br" + i + "{" + (
            ["top-left", "top-right", "bottom-right", "bottom-left"]
        ).map(function(x, j) {
            return i & (1<<j) ? "border-" + x + "-radius: 3px;" : ""
        }).filter(Boolean).join(" ") + "}")
    }
    styles.join("\\n")
    */
  module.exports =
    '\n.ace_br1 {border-top-left-radius    : 3px;}\n.ace_br2 {border-top-right-radius   : 3px;}\n.ace_br3 {border-top-left-radius    : 3px; border-top-right-radius:    3px;}\n.ace_br4 {border-bottom-right-radius: 3px;}\n.ace_br5 {border-top-left-radius    : 3px; border-bottom-right-radius: 3px;}\n.ace_br6 {border-top-right-radius   : 3px; border-bottom-right-radius: 3px;}\n.ace_br7 {border-top-left-radius    : 3px; border-top-right-radius:    3px; border-bottom-right-radius: 3px;}\n.ace_br8 {border-bottom-left-radius : 3px;}\n.ace_br9 {border-top-left-radius    : 3px; border-bottom-left-radius:  3px;}\n.ace_br10{border-top-right-radius   : 3px; border-bottom-left-radius:  3px;}\n.ace_br11{border-top-left-radius    : 3px; border-top-right-radius:    3px; border-bottom-left-radius:  3px;}\n.ace_br12{border-bottom-right-radius: 3px; border-bottom-left-radius:  3px;}\n.ace_br13{border-top-left-radius    : 3px; border-bottom-right-radius: 3px; border-bottom-left-radius:  3px;}\n.ace_br14{border-top-right-radius   : 3px; border-bottom-right-radius: 3px; border-bottom-left-radius:  3px;}\n.ace_br15{border-top-left-radius    : 3px; border-top-right-radius:    3px; border-bottom-right-radius: 3px; border-bottom-left-radius: 3px;}\n\n\n.ace_editor {\n    position: relative;\n    overflow: hidden;\n    padding: 0;\n    font: 12px/normal \'Monaco\', \'Menlo\', \'Ubuntu Mono\', \'Consolas\', \'Source Code Pro\', \'source-code-pro\', monospace;\n    direction: ltr;\n    text-align: left;\n    -webkit-tap-highlight-color: rgba(0, 0, 0, 0);\n}\n\n.ace_scroller {\n    position: absolute;\n    overflow: hidden;\n    top: 0;\n    bottom: 0;\n    background-color: inherit;\n    -ms-user-select: none;\n    -moz-user-select: none;\n    -webkit-user-select: none;\n    user-select: none;\n    cursor: text;\n}\n\n.ace_content {\n    position: absolute;\n    box-sizing: border-box;\n    min-width: 100%;\n    contain: style size layout;\n    font-variant-ligatures: no-common-ligatures;\n}\n\n.ace_keyboard-focus:focus {\n    box-shadow: inset 0 0 0 2px #5E9ED6;\n    outline: none;\n}\n\n.ace_dragging .ace_scroller:before{\n    position: absolute;\n    top: 0;\n    left: 0;\n    right: 0;\n    bottom: 0;\n    content: \'\';\n    background: rgba(250, 250, 250, 0.01);\n    z-index: 1000;\n}\n.ace_dragging.ace_dark .ace_scroller:before{\n    background: rgba(0, 0, 0, 0.01);\n}\n\n.ace_gutter {\n    position: absolute;\n    overflow : hidden;\n    width: auto;\n    top: 0;\n    bottom: 0;\n    left: 0;\n    cursor: default;\n    z-index: 4;\n    -ms-user-select: none;\n    -moz-user-select: none;\n    -webkit-user-select: none;\n    user-select: none;\n    contain: style size layout;\n}\n\n.ace_gutter-active-line {\n    position: absolute;\n    left: 0;\n    right: 0;\n}\n\n.ace_scroller.ace_scroll-left:after {\n    content: "";\n    position: absolute;\n    top: 0;\n    right: 0;\n    bottom: 0;\n    left: 0;\n    box-shadow: 17px 0 16px -16px rgba(0, 0, 0, 0.4) inset;\n    pointer-events: none;\n}\n\n.ace_gutter-cell, .ace_gutter-cell_svg-icons {\n    position: absolute;\n    top: 0;\n    left: 0;\n    right: 0;\n    padding-left: 19px;\n    padding-right: 6px;\n    background-repeat: no-repeat;\n}\n\n.ace_gutter-cell_svg-icons .ace_gutter_annotation {\n    margin-left: -14px;\n    float: left;\n}\n\n.ace_gutter-cell .ace_gutter_annotation {\n    margin-left: -19px;\n    float: left;\n}\n\n.ace_gutter-cell.ace_error, .ace_icon.ace_error, .ace_icon.ace_error_fold {\n    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAABOFBMVEX/////////QRswFAb/Ui4wFAYwFAYwFAaWGAfDRymzOSH/PxswFAb/SiUwFAYwFAbUPRvjQiDllog5HhHdRybsTi3/Tyv9Tir+Syj/UC3////XurebMBIwFAb/RSHbPx/gUzfdwL3kzMivKBAwFAbbvbnhPx66NhowFAYwFAaZJg8wFAaxKBDZurf/RB6mMxb/SCMwFAYwFAbxQB3+RB4wFAb/Qhy4Oh+4QifbNRcwFAYwFAYwFAb/QRzdNhgwFAYwFAbav7v/Uy7oaE68MBK5LxLewr/r2NXewLswFAaxJw4wFAbkPRy2PyYwFAaxKhLm1tMwFAazPiQwFAaUGAb/QBrfOx3bvrv/VC/maE4wFAbRPBq6MRO8Qynew8Dp2tjfwb0wFAbx6eju5+by6uns4uH9/f36+vr/GkHjAAAAYnRSTlMAGt+64rnWu/bo8eAA4InH3+DwoN7j4eLi4xP99Nfg4+b+/u9B/eDs1MD1mO7+4PHg2MXa347g7vDizMLN4eG+Pv7i5evs/v79yu7S3/DV7/498Yv24eH+4ufQ3Ozu/v7+y13sRqwAAADLSURBVHjaZc/XDsFgGIBhtDrshlitmk2IrbHFqL2pvXf/+78DPokj7+Fz9qpU/9UXJIlhmPaTaQ6QPaz0mm+5gwkgovcV6GZzd5JtCQwgsxoHOvJO15kleRLAnMgHFIESUEPmawB9ngmelTtipwwfASilxOLyiV5UVUyVAfbG0cCPHig+GBkzAENHS0AstVF6bacZIOzgLmxsHbt2OecNgJC83JERmePUYq8ARGkJx6XtFsdddBQgZE2nPR6CICZhawjA4Fb/chv+399kfR+MMMDGOQAAAABJRU5ErkJggg==");\n    background-repeat: no-repeat;\n    background-position: 2px center;\n}\n\n.ace_gutter-cell.ace_warning, .ace_icon.ace_warning, .ace_icon.ace_warning_fold {\n    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAmVBMVEX///8AAAD///8AAAAAAABPSzb/5sAAAAB/blH/73z/ulkAAAAAAAD85pkAAAAAAAACAgP/vGz/rkDerGbGrV7/pkQICAf////e0IsAAAD/oED/qTvhrnUAAAD/yHD/njcAAADuv2r/nz//oTj/p064oGf/zHAAAAA9Nir/tFIAAAD/tlTiuWf/tkIAAACynXEAAAAAAAAtIRW7zBpBAAAAM3RSTlMAABR1m7RXO8Ln31Z36zT+neXe5OzooRDfn+TZ4p3h2hTf4t3k3ucyrN1K5+Xaks52Sfs9CXgrAAAAjklEQVR42o3PbQ+CIBQFYEwboPhSYgoYunIqqLn6/z8uYdH8Vmdnu9vz4WwXgN/xTPRD2+sgOcZjsge/whXZgUaYYvT8QnuJaUrjrHUQreGczuEafQCO/SJTufTbroWsPgsllVhq3wJEk2jUSzX3CUEDJC84707djRc5MTAQxoLgupWRwW6UB5fS++NV8AbOZgnsC7BpEAAAAABJRU5ErkJggg==");\n    background-repeat: no-repeat;\n    background-position: 2px center;\n}\n\n.ace_gutter-cell.ace_info, .ace_icon.ace_info {\n    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAAAAAA6mKC9AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAAJ0Uk5TAAB2k804AAAAPklEQVQY02NgIB68QuO3tiLznjAwpKTgNyDbMegwisCHZUETUZV0ZqOquBpXj2rtnpSJT1AEnnRmL2OgGgAAIKkRQap2htgAAAAASUVORK5CYII=");\n    background-repeat: no-repeat;\n    background-position: 2px center;\n}\n.ace_dark .ace_gutter-cell.ace_info, .ace_dark .ace_icon.ace_info {\n    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQBAMAAADt3eJSAAAAJFBMVEUAAAChoaGAgIAqKiq+vr6tra1ZWVmUlJSbm5s8PDxubm56enrdgzg3AAAAAXRSTlMAQObYZgAAAClJREFUeNpjYMAPdsMYHegyJZFQBlsUlMFVCWUYKkAZMxZAGdxlDMQBAG+TBP4B6RyJAAAAAElFTkSuQmCC");\n}\n\n.ace_icon_svg.ace_error {\n    -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMCAxNiI+CjxnIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlPSJyZWQiIHNoYXBlLXJlbmRlcmluZz0iZ2VvbWV0cmljUHJlY2lzaW9uIj4KPGNpcmNsZSBmaWxsPSJub25lIiBjeD0iOCIgY3k9IjgiIHI9IjciIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPGxpbmUgeDE9IjExIiB5MT0iNSIgeDI9IjUiIHkyPSIxMSIvPgo8bGluZSB4MT0iMTEiIHkxPSIxMSIgeDI9IjUiIHkyPSI1Ii8+CjwvZz4KPC9zdmc+");\n    background-color: crimson;\n}\n.ace_icon_svg.ace_warning {\n    -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMCAxNiI+CjxnIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlPSJkYXJrb3JhbmdlIiBzaGFwZS1yZW5kZXJpbmc9Imdlb21ldHJpY1ByZWNpc2lvbiI+Cjxwb2x5Z29uIHN0cm9rZS1saW5lam9pbj0icm91bmQiIGZpbGw9Im5vbmUiIHBvaW50cz0iOCAxIDE1IDE1IDEgMTUgOCAxIi8+CjxyZWN0IHg9IjgiIHk9IjEyIiB3aWR0aD0iMC4wMSIgaGVpZ2h0PSIwLjAxIi8+CjxsaW5lIHgxPSI4IiB5MT0iNiIgeDI9IjgiIHkyPSIxMCIvPgo8L2c+Cjwvc3ZnPg==");\n    background-color: darkorange;\n}\n.ace_icon_svg.ace_info {\n    -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMCAxNiI+CjxnIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlPSJibHVlIiBzaGFwZS1yZW5kZXJpbmc9Imdlb21ldHJpY1ByZWNpc2lvbiI+CjxjaXJjbGUgZmlsbD0ibm9uZSIgY3g9IjgiIGN5PSI4IiByPSI3IiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjxwb2x5bGluZSBwb2ludHM9IjggMTEgOCA4Ii8+Cjxwb2x5bGluZSBwb2ludHM9IjkgOCA2IDgiLz4KPGxpbmUgeDE9IjEwIiB5MT0iMTEiIHgyPSI2IiB5Mj0iMTEiLz4KPHJlY3QgeD0iOCIgeT0iNSIgd2lkdGg9IjAuMDEiIGhlaWdodD0iMC4wMSIvPgo8L2c+Cjwvc3ZnPg==");\n    background-color: royalblue;\n}\n\n.ace_icon_svg.ace_error_fold {\n    -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMCAxNiIgZmlsbD0ibm9uZSI+CiAgPHBhdGggZD0ibSAxOC45Mjk4NTEsNy44Mjk4MDc2IGMgMC4xNDYzNTMsNi4zMzc0NjA0IC02LjMyMzE0Nyw3Ljc3Nzg0NDQgLTcuNDc3OTEyLDcuNzc3ODQ0NCAtMi4xMDcyNzI2LC0wLjEyODc1IDUuMTE3Njc4LDAuMzU2MjQ5IDUuMDUxNjk4LC03Ljg3MDA2MTggLTAuNjA0NjcyLC04LjAwMzk3MzQ5IC03LjA3NzI3MDYsLTcuNTYzMTE4OSAtNC44NTczLC03LjQzMDM5NTU2IDEuNjA2LC0wLjExNTE0MjI1IDYuODk3NDg1LDEuMjYyNTQ1OTYgNy4yODM1MTQsNy41MjI2MTI5NiB6IiBmaWxsPSJjcmltc29uIiBzdHJva2Utd2lkdGg9IjIiLz4KICA8cGF0aCBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGNsaXAtcnVsZT0iZXZlbm9kZCIgZD0ibSA4LjExNDc1NjIsMi4wNTI5ODI4IGMgMy4zNDkxNjk4LDAgNi4wNjQxMzI4LDIuNjc2ODYyNyA2LjA2NDEzMjgsNS45Nzg5NTMgMCwzLjMwMjExMjIgLTIuNzE0OTYzLDUuOTc4OTIwMiAtNi4wNjQxMzI4LDUuOTc4OTIwMiAtMy4zNDkxNDczLDAgLTYuMDY0MTc3MiwtMi42NzY4MDggLTYuMDY0MTc3MiwtNS45Nzg5MjAyIDAuMDA1MzksLTMuMjk5ODg2MSAyLjcxNzI2NTYsLTUuOTczNjQwOCA2LjA2NDE3NzIsLTUuOTc4OTUzIHogbSAwLC0xLjczNTgyNzE5IGMgLTQuMzIxNDgzNiwwIC03LjgyNDc0MDM4LDMuNDU0MDE4NDkgLTcuODI0NzQwMzgsNy43MTQ3ODAxOSAwLDQuMjYwNzI4MiAzLjUwMzI1Njc4LDcuNzE0NzQ1MiA3LjgyNDc0MDM4LDcuNzE0NzQ1MiA0LjMyMTQ0OTgsMCA3LjgyNDY5OTgsLTMuNDU0MDE3IDcuODI0Njk5OCwtNy43MTQ3NDUyIDAsLTIuMDQ2MDkxNCAtMC44MjQzOTIsLTQuMDA4MzY3MiAtMi4yOTE3NTYsLTUuNDU1MTc0NiBDIDEyLjE4MDIyNSwxLjEyOTk2NDggMTAuMTkwMDEzLDAuMzE3MTU1NjEgOC4xMTQ3NTYyLDAuMzE3MTU1NjEgWiBNIDYuOTM3NDU2Myw4LjI0MDU5ODUgNC42NzE4Njg1LDEwLjQ4NTg1MiA2LjAwODY4MTQsMTEuODc2NzI4IDguMzE3MDAzNSw5LjYwMDc5MTEgMTAuNjI1MzM3LDExLjg3NjcyOCAxMS45NjIxMzgsMTAuNDg1ODUyIDkuNjk2NTUwOCw4LjI0MDU5ODUgMTEuOTYyMTM4LDYuMDA2ODA2NiAxMC41NzMyNDYsNC42Mzc0MzM1IDguMzE3MDAzNSw2Ljg3MzQyOTcgNi4wNjA3NjA3LDQuNjM3NDMzNSA0LjY3MTg2ODUsNi4wMDY4MDY2IFoiIGZpbGw9ImNyaW1zb24iIHN0cm9rZS13aWR0aD0iMiIvPgo8L3N2Zz4=");\n    background-color: crimson;\n}\n.ace_icon_svg.ace_warning_fold {\n    -webkit-mask-image: url("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAyMCAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZmlsbC1ydWxlPSJldmVub2RkIiBjbGlwLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik0xNC43NzY5IDE0LjczMzdMOC42NTE5MiAyLjQ4MzY5QzguMzI5NDYgMS44Mzg3NyA3LjQwOTEzIDEuODM4NzcgNy4wODY2NyAyLjQ4MzY5TDAuOTYxNjY5IDE0LjczMzdDMC42NzA3NzUgMTUuMzE1NSAxLjA5MzgzIDE2IDEuNzQ0MjkgMTZIMTMuOTk0M0MxNC42NDQ4IDE2IDE1LjA2NzggMTUuMzE1NSAxNC43NzY5IDE0LjczMzdaTTMuMTYwMDcgMTQuMjVMNy44NjkyOSA0LjgzMTU2TDEyLjU3ODUgMTQuMjVIMy4xNjAwN1pNOC43NDQyOSAxMS42MjVWMTMuMzc1SDYuOTk0MjlWMTEuNjI1SDguNzQ0MjlaTTYuOTk0MjkgMTAuNzVWNy4yNUg4Ljc0NDI5VjEwLjc1SDYuOTk0MjlaIiBmaWxsPSIjRUM3MjExIi8+CjxwYXRoIGQ9Ik0xMS4xOTkxIDIuOTUyMzhDMTAuODgwOSAyLjMxNDY3IDEwLjM1MzcgMS44MDUyNiA5LjcwNTUgMS41MDlMMTEuMDQxIDEuMDY5NzhDMTEuNjg4MyAwLjk0OTgxNCAxMi4zMzcgMS4yNzI2MyAxMi42MzE3IDEuODYxNDFMMTcuNjEzNiAxMS44MTYxQzE4LjM1MjcgMTMuMjkyOSAxNy41OTM4IDE1LjA4MDQgMTYuMDE4IDE1LjU3NDVDMTYuNDA0NCAxNC40NTA3IDE2LjMyMzEgMTMuMjE4OCAxNS43OTI0IDEyLjE1NTVMMTEuMTk5MSAyLjk1MjM4WiIgZmlsbD0iI0VDNzIxMSIvPgo8L3N2Zz4=");\n    background-color: darkorange;\n}\n\n.ace_scrollbar {\n    contain: strict;\n    position: absolute;\n    right: 0;\n    bottom: 0;\n    z-index: 6;\n}\n\n.ace_scrollbar-inner {\n    position: absolute;\n    cursor: text;\n    left: 0;\n    top: 0;\n}\n\n.ace_scrollbar-v{\n    overflow-x: hidden;\n    overflow-y: scroll;\n    top: 0;\n}\n\n.ace_scrollbar-h {\n    overflow-x: scroll;\n    overflow-y: hidden;\n    left: 0;\n}\n\n.ace_print-margin {\n    position: absolute;\n    height: 100%;\n}\n\n.ace_text-input {\n    position: absolute;\n    z-index: 0;\n    width: 0.5em;\n    height: 1em;\n    opacity: 0;\n    background: transparent;\n    -moz-appearance: none;\n    appearance: none;\n    border: none;\n    resize: none;\n    outline: none;\n    overflow: hidden;\n    font: inherit;\n    padding: 0 1px;\n    margin: 0 -1px;\n    contain: strict;\n    -ms-user-select: text;\n    -moz-user-select: text;\n    -webkit-user-select: text;\n    user-select: text;\n    /*with `pre-line` chrome inserts &nbsp; instead of space*/\n    white-space: pre!important;\n}\n.ace_text-input.ace_composition {\n    background: transparent;\n    color: inherit;\n    z-index: 1000;\n    opacity: 1;\n}\n.ace_composition_placeholder { color: transparent }\n.ace_composition_marker { \n    border-bottom: 1px solid;\n    position: absolute;\n    border-radius: 0;\n    margin-top: 1px;\n}\n\n[ace_nocontext=true] {\n    transform: none!important;\n    filter: none!important;\n    clip-path: none!important;\n    mask : none!important;\n    contain: none!important;\n    perspective: none!important;\n    mix-blend-mode: initial!important;\n    z-index: auto;\n}\n\n.ace_layer {\n    z-index: 1;\n    position: absolute;\n    overflow: hidden;\n    /* workaround for chrome bug https://github.com/ajaxorg/ace/issues/2312*/\n    word-wrap: normal;\n    white-space: pre;\n    height: 100%;\n    width: 100%;\n    box-sizing: border-box;\n    /* setting pointer-events: auto; on node under the mouse, which changes\n        during scroll, will break mouse wheel scrolling in Safari */\n    pointer-events: none;\n}\n\n.ace_gutter-layer {\n    position: relative;\n    width: auto;\n    text-align: right;\n    pointer-events: auto;\n    height: 1000000px;\n    contain: style size layout;\n}\n\n.ace_text-layer {\n    font: inherit !important;\n    position: absolute;\n    height: 1000000px;\n    width: 1000000px;\n    contain: style size layout;\n}\n\n.ace_text-layer > .ace_line, .ace_text-layer > .ace_line_group {\n    contain: style size layout;\n    position: absolute;\n    top: 0;\n    left: 0;\n    right: 0;\n}\n\n.ace_hidpi .ace_text-layer,\n.ace_hidpi .ace_gutter-layer,\n.ace_hidpi .ace_content,\n.ace_hidpi .ace_gutter {\n    contain: strict;\n}\n.ace_hidpi .ace_text-layer > .ace_line, \n.ace_hidpi .ace_text-layer > .ace_line_group {\n    contain: strict;\n}\n\n.ace_cjk {\n    display: inline-block;\n    text-align: center;\n}\n\n.ace_cursor-layer {\n    z-index: 4;\n}\n\n.ace_cursor {\n    z-index: 4;\n    position: absolute;\n    box-sizing: border-box;\n    border-left: 2px solid;\n    /* workaround for smooth cursor repaintng whole screen in chrome */\n    transform: translatez(0);\n}\n\n.ace_multiselect .ace_cursor {\n    border-left-width: 1px;\n}\n\n.ace_slim-cursors .ace_cursor {\n    border-left-width: 1px;\n}\n\n.ace_overwrite-cursors .ace_cursor {\n    border-left-width: 0;\n    border-bottom: 1px solid;\n}\n\n.ace_hidden-cursors .ace_cursor {\n    opacity: 0.2;\n}\n\n.ace_hasPlaceholder .ace_hidden-cursors .ace_cursor {\n    opacity: 0;\n}\n\n.ace_smooth-blinking .ace_cursor {\n    transition: opacity 0.18s;\n}\n\n.ace_animate-blinking .ace_cursor {\n    animation-duration: 1000ms;\n    animation-timing-function: step-end;\n    animation-name: blink-ace-animate;\n    animation-iteration-count: infinite;\n}\n\n.ace_animate-blinking.ace_smooth-blinking .ace_cursor {\n    animation-duration: 1000ms;\n    animation-timing-function: ease-in-out;\n    animation-name: blink-ace-animate-smooth;\n}\n    \n@keyframes blink-ace-animate {\n    from, to { opacity: 1; }\n    60% { opacity: 0; }\n}\n\n@keyframes blink-ace-animate-smooth {\n    from, to { opacity: 1; }\n    45% { opacity: 1; }\n    60% { opacity: 0; }\n    85% { opacity: 0; }\n}\n\n.ace_marker-layer .ace_step, .ace_marker-layer .ace_stack {\n    position: absolute;\n    z-index: 3;\n}\n\n.ace_marker-layer .ace_selection {\n    position: absolute;\n    z-index: 5;\n}\n\n.ace_marker-layer .ace_bracket {\n    position: absolute;\n    z-index: 6;\n}\n\n.ace_marker-layer .ace_error_bracket {\n    position: absolute;\n    border-bottom: 1px solid #DE5555;\n    border-radius: 0;\n}\n\n.ace_marker-layer .ace_active-line {\n    position: absolute;\n    z-index: 2;\n}\n\n.ace_marker-layer .ace_selected-word {\n    position: absolute;\n    z-index: 4;\n    box-sizing: border-box;\n}\n\n.ace_line .ace_fold {\n    box-sizing: border-box;\n\n    display: inline-block;\n    height: 11px;\n    margin-top: -2px;\n    vertical-align: middle;\n\n    background-image:\n        url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAJCAYAAADU6McMAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAJpJREFUeNpi/P//PwOlgAXGYGRklAVSokD8GmjwY1wasKljQpYACtpCFeADcHVQfQyMQAwzwAZI3wJKvCLkfKBaMSClBlR7BOQikCFGQEErIH0VqkabiGCAqwUadAzZJRxQr/0gwiXIal8zQQPnNVTgJ1TdawL0T5gBIP1MUJNhBv2HKoQHHjqNrA4WO4zY0glyNKLT2KIfIMAAQsdgGiXvgnYAAAAASUVORK5CYII="),\n        url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAA3CAYAAADNNiA5AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAACJJREFUeNpi+P//fxgTAwPDBxDxD078RSX+YeEyDFMCIMAAI3INmXiwf2YAAAAASUVORK5CYII=");\n    background-repeat: no-repeat, repeat-x;\n    background-position: center center, top left;\n    color: transparent;\n\n    border: 1px solid black;\n    border-radius: 2px;\n\n    cursor: pointer;\n    pointer-events: auto;\n}\n\n.ace_dark .ace_fold {\n}\n\n.ace_fold:hover{\n    background-image:\n        url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAJCAYAAADU6McMAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAJpJREFUeNpi/P//PwOlgAXGYGRklAVSokD8GmjwY1wasKljQpYACtpCFeADcHVQfQyMQAwzwAZI3wJKvCLkfKBaMSClBlR7BOQikCFGQEErIH0VqkabiGCAqwUadAzZJRxQr/0gwiXIal8zQQPnNVTgJ1TdawL0T5gBIP1MUJNhBv2HKoQHHjqNrA4WO4zY0glyNKLT2KIfIMAAQsdgGiXvgnYAAAAASUVORK5CYII="),\n        url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAA3CAYAAADNNiA5AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAACBJREFUeNpi+P//fz4TAwPDZxDxD5X4i5fLMEwJgAADAEPVDbjNw87ZAAAAAElFTkSuQmCC");\n}\n\n.ace_tooltip {\n    background-color: #f5f5f5;\n    border: 1px solid gray;\n    border-radius: 1px;\n    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);\n    color: black;\n    max-width: 100%;\n    padding: 3px 4px;\n    position: fixed;\n    z-index: 999999;\n    box-sizing: border-box;\n    cursor: default;\n    white-space: pre-wrap;\n    word-wrap: break-word;\n    line-height: normal;\n    font-style: normal;\n    font-weight: normal;\n    letter-spacing: normal;\n    pointer-events: none;\n    overflow: auto;\n    max-width: min(60em, 66vw);\n    overscroll-behavior: contain;\n}\n.ace_tooltip pre {\n    white-space: pre-wrap;\n}\n\n.ace_tooltip.ace_dark {\n    background-color: #636363;\n    color: #fff;\n}\n\n.ace_tooltip:focus {\n    outline: 1px solid #5E9ED6;\n}\n\n.ace_icon {\n    display: inline-block;\n    width: 18px;\n    vertical-align: top;\n}\n\n.ace_icon_svg {\n    display: inline-block;\n    width: 12px;\n    vertical-align: top;\n    -webkit-mask-repeat: no-repeat;\n    -webkit-mask-size: 12px;\n    -webkit-mask-position: center;\n}\n\n.ace_folding-enabled > .ace_gutter-cell, .ace_folding-enabled > .ace_gutter-cell_svg-icons {\n    padding-right: 13px;\n}\n\n.ace_fold-widget {\n    box-sizing: border-box;\n\n    margin: 0 -12px 0 1px;\n    display: none;\n    width: 11px;\n    vertical-align: top;\n\n    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAANElEQVR42mWKsQ0AMAzC8ixLlrzQjzmBiEjp0A6WwBCSPgKAXoLkqSot7nN3yMwR7pZ32NzpKkVoDBUxKAAAAABJRU5ErkJggg==");\n    background-repeat: no-repeat;\n    background-position: center;\n\n    border-radius: 3px;\n    \n    border: 1px solid transparent;\n    cursor: pointer;\n}\n\n.ace_folding-enabled .ace_fold-widget {\n    display: inline-block;   \n}\n\n.ace_fold-widget.ace_end {\n    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAANElEQVR42m3HwQkAMAhD0YzsRchFKI7sAikeWkrxwScEB0nh5e7KTPWimZki4tYfVbX+MNl4pyZXejUO1QAAAABJRU5ErkJggg==");\n}\n\n.ace_fold-widget.ace_closed {\n    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAMAAAAGCAYAAAAG5SQMAAAAOUlEQVR42jXKwQkAMAgDwKwqKD4EwQ26sSOkVWjgIIHAzPiCgaqiqnJHZnKICBERHN194O5b9vbLuAVRL+l0YWnZAAAAAElFTkSuQmCCXA==");\n}\n\n.ace_fold-widget:hover {\n    border: 1px solid rgba(0, 0, 0, 0.3);\n    background-color: rgba(255, 255, 255, 0.2);\n    box-shadow: 0 1px 1px rgba(255, 255, 255, 0.7);\n}\n\n.ace_fold-widget:active {\n    border: 1px solid rgba(0, 0, 0, 0.4);\n    background-color: rgba(0, 0, 0, 0.05);\n    box-shadow: 0 1px 1px rgba(255, 255, 255, 0.8);\n}\n/**\n * Dark version for fold widgets\n */\n.ace_dark .ace_fold-widget {\n    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHklEQVQIW2P4//8/AzoGEQ7oGCaLLAhWiSwB146BAQCSTPYocqT0AAAAAElFTkSuQmCC");\n}\n.ace_dark .ace_fold-widget.ace_end {\n    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAH0lEQVQIW2P4//8/AxQ7wNjIAjDMgC4AxjCVKBirIAAF0kz2rlhxpAAAAABJRU5ErkJggg==");\n}\n.ace_dark .ace_fold-widget.ace_closed {\n    background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAMAAAAFCAYAAACAcVaiAAAAHElEQVQIW2P4//+/AxAzgDADlOOAznHAKgPWAwARji8UIDTfQQAAAABJRU5ErkJggg==");\n}\n.ace_dark .ace_fold-widget:hover {\n    box-shadow: 0 1px 1px rgba(255, 255, 255, 0.2);\n    background-color: rgba(255, 255, 255, 0.1);\n}\n.ace_dark .ace_fold-widget:active {\n    box-shadow: 0 1px 1px rgba(255, 255, 255, 0.2);\n}\n\n.ace_inline_button {\n    border: 1px solid lightgray;\n    display: inline-block;\n    margin: -1px 8px;\n    padding: 0 5px;\n    pointer-events: auto;\n    cursor: pointer;\n}\n.ace_inline_button:hover {\n    border-color: gray;\n    background: rgba(200,200,200,0.2);\n    display: inline-block;\n    pointer-events: auto;\n}\n\n.ace_fold-widget.ace_invalid {\n    background-color: #FFB4B4;\n    border-color: #DE5555;\n}\n\n.ace_fade-fold-widgets .ace_fold-widget {\n    transition: opacity 0.4s ease 0.05s;\n    opacity: 0;\n}\n\n.ace_fade-fold-widgets:hover .ace_fold-widget {\n    transition: opacity 0.05s ease 0.05s;\n    opacity:1;\n}\n\n.ace_underline {\n    text-decoration: underline;\n}\n\n.ace_bold {\n    font-weight: bold;\n}\n\n.ace_nobold .ace_bold {\n    font-weight: normal;\n}\n\n.ace_italic {\n    font-style: italic;\n}\n\n\n.ace_error-marker {\n    background-color: rgba(255, 0, 0,0.2);\n    position: absolute;\n    z-index: 9;\n}\n\n.ace_highlight-marker {\n    background-color: rgba(255, 255, 0,0.2);\n    position: absolute;\n    z-index: 8;\n}\n\n.ace_mobile-menu {\n    position: absolute;\n    line-height: 1.5;\n    border-radius: 4px;\n    -ms-user-select: none;\n    -moz-user-select: none;\n    -webkit-user-select: none;\n    user-select: none;\n    background: white;\n    box-shadow: 1px 3px 2px grey;\n    border: 1px solid #dcdcdc;\n    color: black;\n}\n.ace_dark > .ace_mobile-menu {\n    background: #333;\n    color: #ccc;\n    box-shadow: 1px 3px 2px grey;\n    border: 1px solid #444;\n\n}\n.ace_mobile-button {\n    padding: 2px;\n    cursor: pointer;\n    overflow: hidden;\n}\n.ace_mobile-button:hover {\n    background-color: #eee;\n    opacity:1;\n}\n.ace_mobile-button:active {\n    background-color: #ddd;\n}\n\n.ace_placeholder {\n    font-family: arial;\n    transform: scale(0.9);\n    transform-origin: left;\n    white-space: pre;\n    opacity: 0.7;\n    margin: 0 10px;\n}\n\n.ace_ghost_text {\n    opacity: 0.5;\n    font-style: italic;\n    white-space: pre;\n}\n\n.ace_screenreader-only {\n    position:absolute;\n    left:-10000px;\n    top:auto;\n    width:1px;\n    height:1px;\n    overflow:hidden;\n}';
});

define("ace/layer/decorators", [
  "require",
  "exports",
  "module",
  "ace/lib/dom",
  "ace/lib/oop",
  "ace/lib/event_emitter",
], function (require, exports, module) {
  "use strict";
  var dom = require("../lib/dom");
  var oop = require("../lib/oop");
  var EventEmitter = require("../lib/event_emitter").EventEmitter;
  var Decorator = /** @class */ (function () {
    function Decorator(parent, renderer) {
      this.canvas = dom.createElement("canvas");
      this.renderer = renderer;
      this.pixelRatio = 1;
      this.maxHeight = renderer.layerConfig.maxHeight;
      this.lineHeight = renderer.layerConfig.lineHeight;
      this.canvasHeight = parent.parent.scrollHeight;
      this.heightRatio = this.canvasHeight / this.maxHeight;
      this.canvasWidth = parent.width;
      this.minDecorationHeight = (2 * this.pixelRatio) | 0;
      this.halfMinDecorationHeight = (this.minDecorationHeight / 2) | 0;
      this.canvas.width = this.canvasWidth;
      this.canvas.height = this.canvasHeight;
      this.canvas.style.top = 0 + "px";
      this.canvas.style.right = 0 + "px";
      this.canvas.style.zIndex = 7 + "px";
      this.canvas.style.position = "absolute";
      this.colors = {};
      this.colors.dark = {
        error: "rgba(255, 18, 18, 1)",
        warning: "rgba(18, 136, 18, 1)",
        info: "rgba(18, 18, 136, 1)",
      };
      this.colors.light = {
        error: "rgb(255,51,51)",
        warning: "rgb(32,133,72)",
        info: "rgb(35,68,138)",
      };
      parent.element.appendChild(this.canvas);
    }
    Decorator.prototype.$updateDecorators = function (config) {
      var colors =
        this.renderer.theme.isDark === true
          ? this.colors.dark
          : this.colors.light;
      if (config) {
        this.maxHeight = config.maxHeight;
        this.lineHeight = config.lineHeight;
        this.canvasHeight = config.height;
        var allLineHeight = (config.lastRow + 1) * this.lineHeight;
        if (allLineHeight < this.canvasHeight) {
          this.heightRatio = 1;
        } else {
          this.heightRatio = this.canvasHeight / this.maxHeight;
        }
      }
      var ctx = this.canvas.getContext("2d");
      function compare(a, b) {
        if (a.priority < b.priority) return -1;
        if (a.priority > b.priority) return 1;
        return 0;
      }
      var annotations = this.renderer.session.$annotations;
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      if (annotations) {
        var priorities = {
          info: 1,
          warning: 2,
          error: 3,
        };
        annotations.forEach(function (item) {
          item.priority = priorities[item.type] || null;
        });
        annotations = annotations.sort(compare);
        var foldData = this.renderer.session.$foldData;
        for (var i = 0; i < annotations.length; i++) {
          var row = annotations[i].row;
          var compensateFold = this.compensateFoldRows(row, foldData);
          var currentY = Math.round(
            (row - compensateFold) * this.lineHeight * this.heightRatio,
          );
          var y1 = Math.round(
            (row - compensateFold) * this.lineHeight * this.heightRatio,
          );
          var y2 = Math.round(
            ((row - compensateFold) * this.lineHeight + this.lineHeight) *
              this.heightRatio,
          );
          var height = y2 - y1;
          if (height < this.minDecorationHeight) {
            var yCenter = ((y1 + y2) / 2) | 0;
            if (yCenter < this.halfMinDecorationHeight) {
              yCenter = this.halfMinDecorationHeight;
            } else if (
              yCenter + this.halfMinDecorationHeight >
              this.canvasHeight
            ) {
              yCenter = this.canvasHeight - this.halfMinDecorationHeight;
            }
            y1 = Math.round(yCenter - this.halfMinDecorationHeight);
            y2 = Math.round(yCenter + this.halfMinDecorationHeight);
          }
          ctx.fillStyle = colors[annotations[i].type] || null;
          ctx.fillRect(0, currentY, this.canvasWidth, y2 - y1);
        }
      }
      var cursor = this.renderer.session.selection.getCursor();
      if (cursor) {
        var compensateFold = this.compensateFoldRows(cursor.row, foldData);
        var currentY = Math.round(
          (cursor.row - compensateFold) * this.lineHeight * this.heightRatio,
        );
        ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
        ctx.fillRect(0, currentY, this.canvasWidth, 2);
      }
    };
    Decorator.prototype.compensateFoldRows = function (row, foldData) {
      var compensateFold = 0;
      if (foldData && foldData.length > 0) {
        for (var j = 0; j < foldData.length; j++) {
          if (row > foldData[j].start.row && row < foldData[j].end.row) {
            compensateFold += row - foldData[j].start.row;
          } else if (row >= foldData[j].end.row) {
            compensateFold += foldData[j].end.row - foldData[j].start.row;
          }
        }
      }
      return compensateFold;
    };
    return Decorator;
  })();
  oop.implement(Decorator.prototype, EventEmitter);
  exports.Decorator = Decorator;
});

define("ace/virtual_renderer", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/dom",
  "ace/lib/lang",
  "ace/config",
  "ace/layer/gutter",
  "ace/layer/marker",
  "ace/layer/text",
  "ace/layer/cursor",
  "ace/scrollbar",
  "ace/scrollbar",
  "ace/scrollbar_custom",
  "ace/scrollbar_custom",
  "ace/renderloop",
  "ace/layer/font_metrics",
  "ace/lib/event_emitter",
  "ace/css/editor-css",
  "ace/layer/decorators",
  "ace/lib/useragent",
], function (require, exports, module) {
  "use strict";
  var oop = require("./lib/oop");
  var dom = require("./lib/dom");
  var lang = require("./lib/lang");
  var config = require("./config");
  var GutterLayer = require("./layer/gutter").Gutter;
  var MarkerLayer = require("./layer/marker").Marker;
  var TextLayer = require("./layer/text").Text;
  var CursorLayer = require("./layer/cursor").Cursor;
  var HScrollBar = require("./scrollbar").HScrollBar;
  var VScrollBar = require("./scrollbar").VScrollBar;
  var HScrollBarCustom = require("./scrollbar_custom").HScrollBar;
  var VScrollBarCustom = require("./scrollbar_custom").VScrollBar;
  var RenderLoop = require("./renderloop").RenderLoop;
  var FontMetrics = require("./layer/font_metrics").FontMetrics;
  var EventEmitter = require("./lib/event_emitter").EventEmitter;
  var editorCss = require("./css/editor-css");
  var Decorator = require("./layer/decorators").Decorator;
  var useragent = require("./lib/useragent");
  dom.importCssString(editorCss, "ace_editor.css", false);
  var VirtualRenderer = /** @class */ (function () {
    function VirtualRenderer(container, theme) {
      var _self = this;
      this.container = container || dom.createElement("div");
      dom.addCssClass(this.container, "ace_editor");
      if (dom.HI_DPI) dom.addCssClass(this.container, "ace_hidpi");
      this.setTheme(theme);
      if (config.get("useStrictCSP") == null) config.set("useStrictCSP", false);
      this.$gutter = dom.createElement("div");
      this.$gutter.className = "ace_gutter";
      this.container.appendChild(this.$gutter);
      this.$gutter.setAttribute("aria-hidden", "true");
      this.scroller = dom.createElement("div");
      this.scroller.className = "ace_scroller";
      this.container.appendChild(this.scroller);
      this.content = dom.createElement("div");
      this.content.className = "ace_content";
      this.scroller.appendChild(this.content);
      this.$gutterLayer = new GutterLayer(this.$gutter);
      this.$gutterLayer.on("changeGutterWidth", this.onGutterResize.bind(this));
      this.$markerBack = new MarkerLayer(this.content);
      var textLayer = (this.$textLayer = new TextLayer(this.content));
      this.canvas = textLayer.element;
      this.$markerFront = new MarkerLayer(this.content);
      this.$cursorLayer = new CursorLayer(this.content);
      this.$horizScroll = false;
      this.$vScroll = false;
      this.scrollBar = this.scrollBarV = new VScrollBar(this.container, this);
      this.scrollBarH = new HScrollBar(this.container, this);
      this.scrollBarV.on("scroll", function (e) {
        if (!_self.$scrollAnimation)
          _self.session.setScrollTop(e.data - _self.scrollMargin.top);
      });
      this.scrollBarH.on("scroll", function (e) {
        if (!_self.$scrollAnimation)
          _self.session.setScrollLeft(e.data - _self.scrollMargin.left);
      });
      this.scrollTop = 0;
      this.scrollLeft = 0;
      this.cursorPos = {
        row: 0,
        column: 0,
      };
      this.$fontMetrics = new FontMetrics(this.container);
      this.$textLayer.$setFontMetrics(this.$fontMetrics);
      this.$textLayer.on("changeCharacterSize", function (e) {
        _self.updateCharacterSize();
        _self.onResize(
          true,
          _self.gutterWidth,
          _self.$size.width,
          _self.$size.height,
        );
        _self._signal("changeCharacterSize", e);
      });
      this.$size = {
        width: 0,
        height: 0,
        scrollerHeight: 0,
        scrollerWidth: 0,
        $dirty: true,
      };
      this.layerConfig = {
        width: 1,
        padding: 0,
        firstRow: 0,
        firstRowScreen: 0,
        lastRow: 0,
        lineHeight: 0,
        characterWidth: 0,
        minHeight: 1,
        maxHeight: 1,
        offset: 0,
        height: 1,
        gutterOffset: 1,
      };
      this.scrollMargin = {
        left: 0,
        right: 0,
        top: 0,
        bottom: 0,
        v: 0,
        h: 0,
      };
      this.margin = {
        left: 0,
        right: 0,
        top: 0,
        bottom: 0,
        v: 0,
        h: 0,
      };
      this.$keepTextAreaAtCursor = !useragent.isIOS;
      this.$loop = new RenderLoop(
        this.$renderChanges.bind(this),
        this.container.ownerDocument.defaultView,
      );
      this.$loop.schedule(this.CHANGE_FULL);
      this.updateCharacterSize();
      this.setPadding(4);
      this.$addResizeObserver();
      config.resetOptions(this);
      config._signal("renderer", this);
    }
    VirtualRenderer.prototype.updateCharacterSize = function () {
      if (this.$textLayer.allowBoldFonts != this.$allowBoldFonts) {
        this.$allowBoldFonts = this.$textLayer.allowBoldFonts;
        this.setStyle("ace_nobold", !this.$allowBoldFonts);
      }
      this.layerConfig.characterWidth = this.characterWidth =
        this.$textLayer.getCharacterWidth();
      this.layerConfig.lineHeight = this.lineHeight =
        this.$textLayer.getLineHeight();
      this.$updatePrintMargin();
      dom.setStyle(this.scroller.style, "line-height", this.lineHeight + "px");
    };
    VirtualRenderer.prototype.setSession = function (session) {
      if (this.session)
        this.session.doc.off("changeNewLineMode", this.onChangeNewLineMode);
      this.session = session;
      if (session && this.scrollMargin.top && session.getScrollTop() <= 0)
        session.setScrollTop(-this.scrollMargin.top);
      this.$cursorLayer.setSession(session);
      this.$markerBack.setSession(session);
      this.$markerFront.setSession(session);
      this.$gutterLayer.setSession(session);
      this.$textLayer.setSession(session);
      if (!session) return;
      this.$loop.schedule(this.CHANGE_FULL);
      this.session.$setFontMetrics(this.$fontMetrics);
      this.scrollBarH.scrollLeft = this.scrollBarV.scrollTop = null;
      this.onChangeNewLineMode = this.onChangeNewLineMode.bind(this);
      this.onChangeNewLineMode();
      this.session.doc.on("changeNewLineMode", this.onChangeNewLineMode);
    };
    VirtualRenderer.prototype.updateLines = function (
      firstRow,
      lastRow,
      force,
    ) {
      if (lastRow === undefined) lastRow = Infinity;
      if (!this.$changedLines) {
        this.$changedLines = {
          firstRow: firstRow,
          lastRow: lastRow,
        };
      } else {
        if (this.$changedLines.firstRow > firstRow)
          this.$changedLines.firstRow = firstRow;
        if (this.$changedLines.lastRow < lastRow)
          this.$changedLines.lastRow = lastRow;
      }
      if (this.$changedLines.lastRow < this.layerConfig.firstRow) {
        if (force) this.$changedLines.lastRow = this.layerConfig.lastRow;
        else return;
      }
      if (this.$changedLines.firstRow > this.layerConfig.lastRow) return;
      this.$loop.schedule(this.CHANGE_LINES);
    };
    VirtualRenderer.prototype.onChangeNewLineMode = function () {
      this.$loop.schedule(this.CHANGE_TEXT);
      this.$textLayer.$updateEolChar();
      this.session.$bidiHandler.setEolChar(this.$textLayer.EOL_CHAR);
    };
    VirtualRenderer.prototype.onChangeTabSize = function () {
      this.$loop.schedule(this.CHANGE_TEXT | this.CHANGE_MARKER);
      this.$textLayer.onChangeTabSize();
    };
    VirtualRenderer.prototype.updateText = function () {
      this.$loop.schedule(this.CHANGE_TEXT);
    };
    VirtualRenderer.prototype.updateFull = function (force) {
      if (force) this.$renderChanges(this.CHANGE_FULL, true);
      else this.$loop.schedule(this.CHANGE_FULL);
    };
    VirtualRenderer.prototype.updateFontSize = function () {
      this.$textLayer.checkForSizeChanges();
    };
    VirtualRenderer.prototype.$updateSizeAsync = function () {
      if (this.$loop.pending) this.$size.$dirty = true;
      else this.onResize();
    };
    VirtualRenderer.prototype.onResize = function (
      force,
      gutterWidth,
      width,
      height,
    ) {
      if (this.resizing > 2) return;
      else if (this.resizing > 0) this.resizing++;
      else this.resizing = force ? 1 : 0;
      var el = this.container;
      if (!height) height = el.clientHeight || el.scrollHeight;
      if (!width) width = el.clientWidth || el.scrollWidth;
      var changes = this.$updateCachedSize(force, gutterWidth, width, height);
      if (this.$resizeTimer) this.$resizeTimer.cancel();
      if (!this.$size.scrollerHeight || (!width && !height))
        return (this.resizing = 0);
      if (force) this.$gutterLayer.$padding = null;
      if (force) this.$renderChanges(changes | this.$changes, true);
      else this.$loop.schedule(changes | this.$changes);
      if (this.resizing) this.resizing = 0;
      this.scrollBarH.scrollLeft = this.scrollBarV.scrollTop = null;
      if (this.$customScrollbar) {
        this.$updateCustomScrollbar(true);
      }
    };
    VirtualRenderer.prototype.$updateCachedSize = function (
      force,
      gutterWidth,
      width,
      height,
    ) {
      height -= this.$extraHeight || 0;
      var changes = 0;
      var size = this.$size;
      var oldSize = {
        width: size.width,
        height: size.height,
        scrollerHeight: size.scrollerHeight,
        scrollerWidth: size.scrollerWidth,
      };
      if (height && (force || size.height != height)) {
        size.height = height;
        changes |= this.CHANGE_SIZE;
        size.scrollerHeight = size.height;
        if (this.$horizScroll)
          size.scrollerHeight -= this.scrollBarH.getHeight();
        this.scrollBarV.setHeight(size.scrollerHeight);
        this.scrollBarV.element.style.bottom =
          this.scrollBarH.getHeight() + "px";
        changes = changes | this.CHANGE_SCROLL;
      }
      if (width && (force || size.width != width)) {
        changes |= this.CHANGE_SIZE;
        size.width = width;
        if (gutterWidth == null)
          gutterWidth = this.$showGutter ? this.$gutter.offsetWidth : 0;
        this.gutterWidth = gutterWidth;
        dom.setStyle(this.scrollBarH.element.style, "left", gutterWidth + "px");
        dom.setStyle(
          this.scroller.style,
          "left",
          gutterWidth + this.margin.left + "px",
        );
        size.scrollerWidth = Math.max(
          0,
          width - gutterWidth - this.scrollBarV.getWidth() - this.margin.h,
        );
        dom.setStyle(this.$gutter.style, "left", this.margin.left + "px");
        var right = this.scrollBarV.getWidth() + "px";
        dom.setStyle(this.scrollBarH.element.style, "right", right);
        dom.setStyle(this.scroller.style, "right", right);
        dom.setStyle(
          this.scroller.style,
          "bottom",
          this.scrollBarH.getHeight(),
        );
        this.scrollBarH.setWidth(size.scrollerWidth);
        if (
          (this.session &&
            this.session.getUseWrapMode() &&
            this.adjustWrapLimit()) ||
          force
        ) {
          changes |= this.CHANGE_FULL;
        }
      }
      size.$dirty = !width || !height;
      if (changes) this._signal("resize", oldSize);
      return changes;
    };
    VirtualRenderer.prototype.onGutterResize = function (width) {
      var gutterWidth = this.$showGutter ? width : 0;
      if (gutterWidth != this.gutterWidth)
        this.$changes |= this.$updateCachedSize(
          true,
          gutterWidth,
          this.$size.width,
          this.$size.height,
        );
      if (this.session.getUseWrapMode() && this.adjustWrapLimit()) {
        this.$loop.schedule(this.CHANGE_FULL);
      } else if (this.$size.$dirty) {
        this.$loop.schedule(this.CHANGE_FULL);
      } else {
        this.$computeLayerConfig();
      }
    };
    VirtualRenderer.prototype.adjustWrapLimit = function () {
      var availableWidth = this.$size.scrollerWidth - this.$padding * 2;
      var limit = Math.floor(availableWidth / this.characterWidth);
      return this.session.adjustWrapLimit(
        limit,
        this.$showPrintMargin && this.$printMarginColumn,
      );
    };
    VirtualRenderer.prototype.setAnimatedScroll = function (shouldAnimate) {
      this.setOption("animatedScroll", shouldAnimate);
    };
    VirtualRenderer.prototype.getAnimatedScroll = function () {
      return this.$animatedScroll;
    };
    VirtualRenderer.prototype.setShowInvisibles = function (showInvisibles) {
      this.setOption("showInvisibles", showInvisibles);
      this.session.$bidiHandler.setShowInvisibles(showInvisibles);
    };
    VirtualRenderer.prototype.getShowInvisibles = function () {
      return this.getOption("showInvisibles");
    };
    VirtualRenderer.prototype.getDisplayIndentGuides = function () {
      return this.getOption("displayIndentGuides");
    };
    VirtualRenderer.prototype.setDisplayIndentGuides = function (display) {
      this.setOption("displayIndentGuides", display);
    };
    VirtualRenderer.prototype.getHighlightIndentGuides = function () {
      return this.getOption("highlightIndentGuides");
    };
    VirtualRenderer.prototype.setHighlightIndentGuides = function (highlight) {
      this.setOption("highlightIndentGuides", highlight);
    };
    VirtualRenderer.prototype.setShowPrintMargin = function (showPrintMargin) {
      this.setOption("showPrintMargin", showPrintMargin);
    };
    VirtualRenderer.prototype.getShowPrintMargin = function () {
      return this.getOption("showPrintMargin");
    };
    VirtualRenderer.prototype.setPrintMarginColumn = function (
      printMarginColumn,
    ) {
      this.setOption("printMarginColumn", printMarginColumn);
    };
    VirtualRenderer.prototype.getPrintMarginColumn = function () {
      return this.getOption("printMarginColumn");
    };
    VirtualRenderer.prototype.getShowGutter = function () {
      return this.getOption("showGutter");
    };
    VirtualRenderer.prototype.setShowGutter = function (show) {
      return this.setOption("showGutter", show);
    };
    VirtualRenderer.prototype.getFadeFoldWidgets = function () {
      return this.getOption("fadeFoldWidgets");
    };
    VirtualRenderer.prototype.setFadeFoldWidgets = function (show) {
      this.setOption("fadeFoldWidgets", show);
    };
    VirtualRenderer.prototype.setHighlightGutterLine = function (
      shouldHighlight,
    ) {
      this.setOption("highlightGutterLine", shouldHighlight);
    };
    VirtualRenderer.prototype.getHighlightGutterLine = function () {
      return this.getOption("highlightGutterLine");
    };
    VirtualRenderer.prototype.$updatePrintMargin = function () {
      if (!this.$showPrintMargin && !this.$printMarginEl) return;
      if (!this.$printMarginEl) {
        var containerEl = dom.createElement("div");
        containerEl.className = "ace_layer ace_print-margin-layer";
        this.$printMarginEl = dom.createElement("div");
        this.$printMarginEl.className = "ace_print-margin";
        containerEl.appendChild(this.$printMarginEl);
        this.content.insertBefore(containerEl, this.content.firstChild);
      }
      var style = this.$printMarginEl.style;
      style.left =
        Math.round(
          this.characterWidth * this.$printMarginColumn + this.$padding,
        ) + "px";
      style.visibility = this.$showPrintMargin ? "visible" : "hidden";
      if (this.session && this.session.$wrap == -1) this.adjustWrapLimit();
    };
    VirtualRenderer.prototype.getContainerElement = function () {
      return this.container;
    };
    VirtualRenderer.prototype.getMouseEventTarget = function () {
      return this.scroller;
    };
    VirtualRenderer.prototype.getTextAreaContainer = function () {
      return this.container;
    };
    VirtualRenderer.prototype.$moveTextAreaToCursor = function () {
      if (this.$isMousePressed) return;
      var style = this.textarea.style;
      var composition = this.$composition;
      if (!this.$keepTextAreaAtCursor && !composition) {
        dom.translate(this.textarea, -100, 0);
        return;
      }
      var pixelPos = this.$cursorLayer.$pixelPos;
      if (!pixelPos) return;
      if (composition && composition.markerRange)
        pixelPos = this.$cursorLayer.getPixelPosition(
          composition.markerRange.start,
          true,
        );
      var config = this.layerConfig;
      var posTop = pixelPos.top;
      var posLeft = pixelPos.left;
      posTop -= config.offset;
      var h =
        (composition && composition.useTextareaForIME) || useragent.isMobile
          ? this.lineHeight
          : 1;
      if (posTop < 0 || posTop > config.height - h) {
        dom.translate(this.textarea, 0, 0);
        return;
      }
      var w = 1;
      var maxTop = this.$size.height - h;
      if (!composition) {
        posTop += this.lineHeight;
      } else {
        if (composition.useTextareaForIME) {
          var val = this.textarea.value;
          w = this.characterWidth * this.session.$getStringScreenWidth(val)[0];
        } else {
          posTop += this.lineHeight + 2;
        }
      }
      posLeft -= this.scrollLeft;
      if (posLeft > this.$size.scrollerWidth - w)
        posLeft = this.$size.scrollerWidth - w;
      posLeft += this.gutterWidth + this.margin.left;
      dom.setStyle(style, "height", h + "px");
      dom.setStyle(style, "width", w + "px");
      dom.translate(
        this.textarea,
        Math.min(posLeft, this.$size.scrollerWidth - w),
        Math.min(posTop, maxTop),
      );
    };
    VirtualRenderer.prototype.getFirstVisibleRow = function () {
      return this.layerConfig.firstRow;
    };
    VirtualRenderer.prototype.getFirstFullyVisibleRow = function () {
      return (
        this.layerConfig.firstRow + (this.layerConfig.offset === 0 ? 0 : 1)
      );
    };
    VirtualRenderer.prototype.getLastFullyVisibleRow = function () {
      var config = this.layerConfig;
      var lastRow = config.lastRow;
      var top =
        this.session.documentToScreenRow(lastRow, 0) * config.lineHeight;
      if (top - this.session.getScrollTop() > config.height - config.lineHeight)
        return lastRow - 1;
      return lastRow;
    };
    VirtualRenderer.prototype.getLastVisibleRow = function () {
      return this.layerConfig.lastRow;
    };
    VirtualRenderer.prototype.setPadding = function (padding) {
      this.$padding = padding;
      this.$textLayer.setPadding(padding);
      this.$cursorLayer.setPadding(padding);
      this.$markerFront.setPadding(padding);
      this.$markerBack.setPadding(padding);
      this.$loop.schedule(this.CHANGE_FULL);
      this.$updatePrintMargin();
    };
    VirtualRenderer.prototype.setScrollMargin = function (
      top,
      bottom,
      left,
      right,
    ) {
      var sm = this.scrollMargin;
      sm.top = top | 0;
      sm.bottom = bottom | 0;
      sm.right = right | 0;
      sm.left = left | 0;
      sm.v = sm.top + sm.bottom;
      sm.h = sm.left + sm.right;
      if (sm.top && this.scrollTop <= 0 && this.session)
        this.session.setScrollTop(-sm.top);
      this.updateFull();
    };
    VirtualRenderer.prototype.setMargin = function (top, bottom, left, right) {
      var sm = this.margin;
      sm.top = top | 0;
      sm.bottom = bottom | 0;
      sm.right = right | 0;
      sm.left = left | 0;
      sm.v = sm.top + sm.bottom;
      sm.h = sm.left + sm.right;
      this.$updateCachedSize(
        true,
        this.gutterWidth,
        this.$size.width,
        this.$size.height,
      );
      this.updateFull();
    };
    VirtualRenderer.prototype.getHScrollBarAlwaysVisible = function () {
      return this.$hScrollBarAlwaysVisible;
    };
    VirtualRenderer.prototype.setHScrollBarAlwaysVisible = function (
      alwaysVisible,
    ) {
      this.setOption("hScrollBarAlwaysVisible", alwaysVisible);
    };
    VirtualRenderer.prototype.getVScrollBarAlwaysVisible = function () {
      return this.$vScrollBarAlwaysVisible;
    };
    VirtualRenderer.prototype.setVScrollBarAlwaysVisible = function (
      alwaysVisible,
    ) {
      this.setOption("vScrollBarAlwaysVisible", alwaysVisible);
    };
    VirtualRenderer.prototype.$updateScrollBarV = function () {
      var scrollHeight = this.layerConfig.maxHeight;
      var scrollerHeight = this.$size.scrollerHeight;
      if (!this.$maxLines && this.$scrollPastEnd) {
        scrollHeight -=
          (scrollerHeight - this.lineHeight) * this.$scrollPastEnd;
        if (this.scrollTop > scrollHeight - scrollerHeight) {
          scrollHeight = this.scrollTop + scrollerHeight;
          this.scrollBarV.scrollTop = null;
        }
      }
      this.scrollBarV.setScrollHeight(scrollHeight + this.scrollMargin.v);
      this.scrollBarV.setScrollTop(this.scrollTop + this.scrollMargin.top);
    };
    VirtualRenderer.prototype.$updateScrollBarH = function () {
      this.scrollBarH.setScrollWidth(
        this.layerConfig.width + 2 * this.$padding + this.scrollMargin.h,
      );
      this.scrollBarH.setScrollLeft(this.scrollLeft + this.scrollMargin.left);
    };
    VirtualRenderer.prototype.freeze = function () {
      this.$frozen = true;
    };
    VirtualRenderer.prototype.unfreeze = function () {
      this.$frozen = false;
    };
    VirtualRenderer.prototype.$renderChanges = function (changes, force) {
      if (this.$changes) {
        changes |= this.$changes;
        this.$changes = 0;
      }
      if (
        !this.session ||
        !this.container.offsetWidth ||
        this.$frozen ||
        (!changes && !force)
      ) {
        this.$changes |= changes;
        return;
      }
      if (this.$size.$dirty) {
        this.$changes |= changes;
        return this.onResize(true);
      }
      if (!this.lineHeight) {
        this.$textLayer.checkForSizeChanges();
      }
      this._signal("beforeRender", changes);
      if (this.session && this.session.$bidiHandler)
        this.session.$bidiHandler.updateCharacterWidths(this.$fontMetrics);
      var config = this.layerConfig;
      if (
        changes & this.CHANGE_FULL ||
        changes & this.CHANGE_SIZE ||
        changes & this.CHANGE_TEXT ||
        changes & this.CHANGE_LINES ||
        changes & this.CHANGE_SCROLL ||
        changes & this.CHANGE_H_SCROLL
      ) {
        changes |= this.$computeLayerConfig() | this.$loop.clear();
        if (
          config.firstRow != this.layerConfig.firstRow &&
          config.firstRowScreen == this.layerConfig.firstRowScreen
        ) {
          var st =
            this.scrollTop +
            (config.firstRow - Math.max(this.layerConfig.firstRow, 0)) *
              this.lineHeight;
          if (st > 0) {
            this.scrollTop = st;
            changes = changes | this.CHANGE_SCROLL;
            changes |= this.$computeLayerConfig() | this.$loop.clear();
          }
        }
        config = this.layerConfig;
        this.$updateScrollBarV();
        if (changes & this.CHANGE_H_SCROLL) this.$updateScrollBarH();
        dom.translate(this.content, -this.scrollLeft, -config.offset);
        var width = config.width + 2 * this.$padding + "px";
        var height = config.minHeight + "px";
        dom.setStyle(this.content.style, "width", width);
        dom.setStyle(this.content.style, "height", height);
      }
      if (changes & this.CHANGE_H_SCROLL) {
        dom.translate(this.content, -this.scrollLeft, -config.offset);
        this.scroller.className =
          this.scrollLeft <= 0
            ? "ace_scroller "
            : "ace_scroller ace_scroll-left ";
        if (this.enableKeyboardAccessibility)
          this.scroller.className += this.keyboardFocusClassName;
      }
      if (changes & this.CHANGE_FULL) {
        this.$changedLines = null;
        this.$textLayer.update(config);
        if (this.$showGutter) this.$gutterLayer.update(config);
        if (this.$customScrollbar) {
          this.$scrollDecorator.$updateDecorators(config);
        }
        this.$markerBack.update(config);
        this.$markerFront.update(config);
        this.$cursorLayer.update(config);
        this.$moveTextAreaToCursor();
        this._signal("afterRender", changes);
        return;
      }
      if (changes & this.CHANGE_SCROLL) {
        this.$changedLines = null;
        if (changes & this.CHANGE_TEXT || changes & this.CHANGE_LINES)
          this.$textLayer.update(config);
        else this.$textLayer.scrollLines(config);
        if (this.$showGutter) {
          if (changes & this.CHANGE_GUTTER || changes & this.CHANGE_LINES)
            this.$gutterLayer.update(config);
          else this.$gutterLayer.scrollLines(config);
        }
        if (this.$customScrollbar) {
          this.$scrollDecorator.$updateDecorators(config);
        }
        this.$markerBack.update(config);
        this.$markerFront.update(config);
        this.$cursorLayer.update(config);
        this.$moveTextAreaToCursor();
        this._signal("afterRender", changes);
        return;
      }
      if (changes & this.CHANGE_TEXT) {
        this.$changedLines = null;
        this.$textLayer.update(config);
        if (this.$showGutter) this.$gutterLayer.update(config);
        if (this.$customScrollbar) {
          this.$scrollDecorator.$updateDecorators(config);
        }
      } else if (changes & this.CHANGE_LINES) {
        if (
          this.$updateLines() ||
          (changes & this.CHANGE_GUTTER && this.$showGutter)
        )
          this.$gutterLayer.update(config);
        if (this.$customScrollbar) {
          this.$scrollDecorator.$updateDecorators(config);
        }
      } else if (changes & this.CHANGE_TEXT || changes & this.CHANGE_GUTTER) {
        if (this.$showGutter) this.$gutterLayer.update(config);
        if (this.$customScrollbar) {
          this.$scrollDecorator.$updateDecorators(config);
        }
      } else if (changes & this.CHANGE_CURSOR) {
        if (this.$highlightGutterLine)
          this.$gutterLayer.updateLineHighlight(config);
        if (this.$customScrollbar) {
          this.$scrollDecorator.$updateDecorators(config);
        }
      }
      if (changes & this.CHANGE_CURSOR) {
        this.$cursorLayer.update(config);
        this.$moveTextAreaToCursor();
      }
      if (changes & (this.CHANGE_MARKER | this.CHANGE_MARKER_FRONT)) {
        this.$markerFront.update(config);
      }
      if (changes & (this.CHANGE_MARKER | this.CHANGE_MARKER_BACK)) {
        this.$markerBack.update(config);
      }
      this._signal("afterRender", changes);
    };
    VirtualRenderer.prototype.$autosize = function () {
      var height = this.session.getScreenLength() * this.lineHeight;
      var maxHeight = this.$maxLines * this.lineHeight;
      var desiredHeight =
        Math.min(
          maxHeight,
          Math.max((this.$minLines || 1) * this.lineHeight, height),
        ) +
        this.scrollMargin.v +
        (this.$extraHeight || 0);
      if (this.$horizScroll) desiredHeight += this.scrollBarH.getHeight();
      if (this.$maxPixelHeight && desiredHeight > this.$maxPixelHeight)
        desiredHeight = this.$maxPixelHeight;
      var hideScrollbars = desiredHeight <= 2 * this.lineHeight;
      var vScroll = !hideScrollbars && height > maxHeight;
      if (
        desiredHeight != this.desiredHeight ||
        this.$size.height != this.desiredHeight ||
        vScroll != this.$vScroll
      ) {
        if (vScroll != this.$vScroll) {
          this.$vScroll = vScroll;
          this.scrollBarV.setVisible(vScroll);
        }
        var w = this.container.clientWidth;
        this.container.style.height = desiredHeight + "px";
        this.$updateCachedSize(true, this.$gutterWidth, w, desiredHeight);
        this.desiredHeight = desiredHeight;
        this._signal("autosize");
      }
    };
    VirtualRenderer.prototype.$computeLayerConfig = function () {
      var session = this.session;
      var size = this.$size;
      var hideScrollbars = size.height <= 2 * this.lineHeight;
      var screenLines = this.session.getScreenLength();
      var maxHeight = screenLines * this.lineHeight;
      var longestLine = this.$getLongestLine();
      var horizScroll =
        !hideScrollbars &&
        (this.$hScrollBarAlwaysVisible ||
          size.scrollerWidth - longestLine - 2 * this.$padding < 0);
      var hScrollChanged = this.$horizScroll !== horizScroll;
      if (hScrollChanged) {
        this.$horizScroll = horizScroll;
        this.scrollBarH.setVisible(horizScroll);
      }
      var vScrollBefore = this.$vScroll; // autosize can change vscroll value in which case we need to update longestLine
      if (this.$maxLines && this.lineHeight > 1) this.$autosize();
      var minHeight = size.scrollerHeight + this.lineHeight;
      var scrollPastEnd =
        !this.$maxLines && this.$scrollPastEnd
          ? (size.scrollerHeight - this.lineHeight) * this.$scrollPastEnd
          : 0;
      maxHeight += scrollPastEnd;
      var sm = this.scrollMargin;
      this.session.setScrollTop(
        Math.max(
          -sm.top,
          Math.min(this.scrollTop, maxHeight - size.scrollerHeight + sm.bottom),
        ),
      );
      this.session.setScrollLeft(
        Math.max(
          -sm.left,
          Math.min(
            this.scrollLeft,
            longestLine + 2 * this.$padding - size.scrollerWidth + sm.right,
          ),
        ),
      );
      var vScroll =
        !hideScrollbars &&
        (this.$vScrollBarAlwaysVisible ||
          size.scrollerHeight - maxHeight + scrollPastEnd < 0 ||
          this.scrollTop > sm.top);
      var vScrollChanged = vScrollBefore !== vScroll;
      if (vScrollChanged) {
        this.$vScroll = vScroll;
        this.scrollBarV.setVisible(vScroll);
      }
      var offset = this.scrollTop % this.lineHeight;
      var lineCount = Math.ceil(minHeight / this.lineHeight) - 1;
      var firstRow = Math.max(
        0,
        Math.round((this.scrollTop - offset) / this.lineHeight),
      );
      var lastRow = firstRow + lineCount;
      var firstRowScreen, firstRowHeight;
      var lineHeight = this.lineHeight;
      firstRow = session.screenToDocumentRow(firstRow, 0);
      var foldLine = session.getFoldLine(firstRow);
      if (foldLine) {
        firstRow = foldLine.start.row;
      }
      firstRowScreen = session.documentToScreenRow(firstRow, 0);
      firstRowHeight = session.getRowLength(firstRow) * lineHeight;
      lastRow = Math.min(
        session.screenToDocumentRow(lastRow, 0),
        session.getLength() - 1,
      );
      minHeight =
        size.scrollerHeight +
        session.getRowLength(lastRow) * lineHeight +
        firstRowHeight;
      offset = this.scrollTop - firstRowScreen * lineHeight;
      var changes = 0;
      if (this.layerConfig.width != longestLine || hScrollChanged)
        changes = this.CHANGE_H_SCROLL;
      if (hScrollChanged || vScrollChanged) {
        changes |= this.$updateCachedSize(
          true,
          this.gutterWidth,
          size.width,
          size.height,
        );
        this._signal("scrollbarVisibilityChanged");
        if (vScrollChanged) longestLine = this.$getLongestLine();
      }
      this.layerConfig = {
        width: longestLine,
        padding: this.$padding,
        firstRow: firstRow,
        firstRowScreen: firstRowScreen,
        lastRow: lastRow,
        lineHeight: lineHeight,
        characterWidth: this.characterWidth,
        minHeight: minHeight,
        maxHeight: maxHeight,
        offset: offset,
        gutterOffset: lineHeight
          ? Math.max(
              0,
              Math.ceil(
                (offset + size.height - size.scrollerHeight) / lineHeight,
              ),
            )
          : 0,
        height: this.$size.scrollerHeight,
      };
      if (this.session.$bidiHandler)
        this.session.$bidiHandler.setContentWidth(longestLine - this.$padding);
      return changes;
    };
    VirtualRenderer.prototype.$updateLines = function () {
      if (!this.$changedLines) return;
      var firstRow = this.$changedLines.firstRow;
      var lastRow = this.$changedLines.lastRow;
      this.$changedLines = null;
      var layerConfig = this.layerConfig;
      if (firstRow > layerConfig.lastRow + 1) {
        return;
      }
      if (lastRow < layerConfig.firstRow) {
        return;
      }
      if (lastRow === Infinity) {
        if (this.$showGutter) this.$gutterLayer.update(layerConfig);
        this.$textLayer.update(layerConfig);
        return;
      }
      this.$textLayer.updateLines(layerConfig, firstRow, lastRow);
      return true;
    };
    VirtualRenderer.prototype.$getLongestLine = function () {
      var charCount = this.session.getScreenWidth();
      if (this.showInvisibles && !this.session.$useWrapMode) charCount += 1;
      if (this.$textLayer && charCount > this.$textLayer.MAX_LINE_LENGTH)
        charCount = this.$textLayer.MAX_LINE_LENGTH + 30;
      return Math.max(
        this.$size.scrollerWidth - 2 * this.$padding,
        Math.round(charCount * this.characterWidth),
      );
    };
    VirtualRenderer.prototype.updateFrontMarkers = function () {
      this.$markerFront.setMarkers(this.session.getMarkers(true));
      this.$loop.schedule(this.CHANGE_MARKER_FRONT);
    };
    VirtualRenderer.prototype.updateBackMarkers = function () {
      this.$markerBack.setMarkers(this.session.getMarkers());
      this.$loop.schedule(this.CHANGE_MARKER_BACK);
    };
    VirtualRenderer.prototype.addGutterDecoration = function (row, className) {
      this.$gutterLayer.addGutterDecoration(row, className);
    };
    VirtualRenderer.prototype.removeGutterDecoration = function (
      row,
      className,
    ) {
      this.$gutterLayer.removeGutterDecoration(row, className);
    };
    VirtualRenderer.prototype.updateBreakpoints = function (rows) {
      this._rows = rows;
      this.$loop.schedule(this.CHANGE_GUTTER);
    };
    VirtualRenderer.prototype.setAnnotations = function (annotations) {
      this.$gutterLayer.setAnnotations(annotations);
      this.$loop.schedule(this.CHANGE_GUTTER);
    };
    VirtualRenderer.prototype.updateCursor = function () {
      this.$loop.schedule(this.CHANGE_CURSOR);
    };
    VirtualRenderer.prototype.hideCursor = function () {
      this.$cursorLayer.hideCursor();
    };
    VirtualRenderer.prototype.showCursor = function () {
      this.$cursorLayer.showCursor();
    };
    VirtualRenderer.prototype.scrollSelectionIntoView = function (
      anchor,
      lead,
      offset,
    ) {
      this.scrollCursorIntoView(anchor, offset);
      this.scrollCursorIntoView(lead, offset);
    };
    VirtualRenderer.prototype.scrollCursorIntoView = function (
      cursor,
      offset,
      $viewMargin,
    ) {
      if (this.$size.scrollerHeight === 0) return;
      var pos = this.$cursorLayer.getPixelPosition(cursor);
      var newLeft = pos.left;
      var newTop = pos.top;
      var topMargin = ($viewMargin && $viewMargin.top) || 0;
      var bottomMargin = ($viewMargin && $viewMargin.bottom) || 0;
      if (this.$scrollAnimation) {
        this.$stopAnimation = true;
      }
      var currentTop = this.$scrollAnimation
        ? this.session.getScrollTop()
        : this.scrollTop;
      if (currentTop + topMargin > newTop) {
        if (offset && currentTop + topMargin > newTop + this.lineHeight)
          newTop -= offset * this.$size.scrollerHeight;
        if (newTop === 0) newTop = -this.scrollMargin.top;
        this.session.setScrollTop(newTop);
      } else if (
        currentTop + this.$size.scrollerHeight - bottomMargin <
        newTop + this.lineHeight
      ) {
        if (
          offset &&
          currentTop + this.$size.scrollerHeight - bottomMargin <
            newTop - this.lineHeight
        )
          newTop += offset * this.$size.scrollerHeight;
        this.session.setScrollTop(
          newTop + this.lineHeight + bottomMargin - this.$size.scrollerHeight,
        );
      }
      var currentLeft = this.scrollLeft;
      var twoCharsWidth = 2 * this.layerConfig.characterWidth;
      if (newLeft - twoCharsWidth < currentLeft) {
        newLeft -= twoCharsWidth;
        if (newLeft < this.$padding + twoCharsWidth) {
          newLeft = -this.scrollMargin.left;
        }
        this.session.setScrollLeft(newLeft);
      } else {
        newLeft += twoCharsWidth;
        if (
          currentLeft + this.$size.scrollerWidth <
          newLeft + this.characterWidth
        ) {
          this.session.setScrollLeft(
            Math.round(
              newLeft + this.characterWidth - this.$size.scrollerWidth,
            ),
          );
        } else if (
          currentLeft <= this.$padding &&
          newLeft - currentLeft < this.characterWidth
        ) {
          this.session.setScrollLeft(0);
        }
      }
    };
    VirtualRenderer.prototype.getScrollTop = function () {
      return this.session.getScrollTop();
    };
    VirtualRenderer.prototype.getScrollLeft = function () {
      return this.session.getScrollLeft();
    };
    VirtualRenderer.prototype.getScrollTopRow = function () {
      return this.scrollTop / this.lineHeight;
    };
    VirtualRenderer.prototype.getScrollBottomRow = function () {
      return Math.max(
        0,
        Math.floor(
          (this.scrollTop + this.$size.scrollerHeight) / this.lineHeight,
        ) - 1,
      );
    };
    VirtualRenderer.prototype.scrollToRow = function (row) {
      this.session.setScrollTop(row * this.lineHeight);
    };
    VirtualRenderer.prototype.alignCursor = function (cursor, alignment) {
      if (typeof cursor == "number") cursor = { row: cursor, column: 0 };
      var pos = this.$cursorLayer.getPixelPosition(cursor);
      var h = this.$size.scrollerHeight - this.lineHeight;
      var offset = pos.top - h * (alignment || 0);
      this.session.setScrollTop(offset);
      return offset;
    };
    VirtualRenderer.prototype.$calcSteps = function (fromValue, toValue) {
      var i = 0;
      var l = this.STEPS;
      var steps = [];
      var func = function (t, x_min, dx) {
        return dx * (Math.pow(t - 1, 3) + 1) + x_min;
      };
      for (i = 0; i < l; ++i)
        steps.push(func(i / this.STEPS, fromValue, toValue - fromValue));
      return steps;
    };
    VirtualRenderer.prototype.scrollToLine = function (
      line,
      center,
      animate,
      callback,
    ) {
      var pos = this.$cursorLayer.getPixelPosition({ row: line, column: 0 });
      var offset = pos.top;
      if (center) offset -= this.$size.scrollerHeight / 2;
      var initialScroll = this.scrollTop;
      this.session.setScrollTop(offset);
      if (animate !== false) this.animateScrolling(initialScroll, callback);
    };
    VirtualRenderer.prototype.animateScrolling = function (
      fromValue,
      callback,
    ) {
      var toValue = this.scrollTop;
      if (!this.$animatedScroll) return;
      var _self = this;
      if (fromValue == toValue) return;
      if (this.$scrollAnimation) {
        var oldSteps = this.$scrollAnimation.steps;
        if (oldSteps.length) {
          fromValue = oldSteps[0];
          if (fromValue == toValue) return;
        }
      }
      var steps = _self.$calcSteps(fromValue, toValue);
      this.$scrollAnimation = { from: fromValue, to: toValue, steps: steps };
      clearInterval(this.$timer);
      _self.session.setScrollTop(steps.shift());
      _self.session.$scrollTop = toValue;
      function endAnimation() {
        _self.$timer = clearInterval(_self.$timer);
        _self.$scrollAnimation = null;
        _self.$stopAnimation = false;
        callback && callback();
      }
      this.$timer = setInterval(function () {
        if (_self.$stopAnimation) {
          endAnimation();
          return;
        }
        if (!_self.session) return clearInterval(_self.$timer);
        if (steps.length) {
          _self.session.setScrollTop(steps.shift());
          _self.session.$scrollTop = toValue;
        } else if (toValue != null) {
          _self.session.$scrollTop = -1;
          _self.session.setScrollTop(toValue);
          toValue = null;
        } else {
          endAnimation();
        }
      }, 10);
    };
    VirtualRenderer.prototype.scrollToY = function (scrollTop) {
      if (this.scrollTop !== scrollTop) {
        this.$loop.schedule(this.CHANGE_SCROLL);
        this.scrollTop = scrollTop;
      }
    };
    VirtualRenderer.prototype.scrollToX = function (scrollLeft) {
      if (this.scrollLeft !== scrollLeft) this.scrollLeft = scrollLeft;
      this.$loop.schedule(this.CHANGE_H_SCROLL);
    };
    VirtualRenderer.prototype.scrollTo = function (x, y) {
      this.session.setScrollTop(y);
      this.session.setScrollLeft(x);
    };
    VirtualRenderer.prototype.scrollBy = function (deltaX, deltaY) {
      deltaY && this.session.setScrollTop(this.session.getScrollTop() + deltaY);
      deltaX &&
        this.session.setScrollLeft(this.session.getScrollLeft() + deltaX);
    };
    VirtualRenderer.prototype.isScrollableBy = function (deltaX, deltaY) {
      if (
        deltaY < 0 &&
        this.session.getScrollTop() >= 1 - this.scrollMargin.top
      )
        return true;
      if (
        deltaY > 0 &&
        this.session.getScrollTop() +
          this.$size.scrollerHeight -
          this.layerConfig.maxHeight <
          -1 + this.scrollMargin.bottom
      )
        return true;
      if (
        deltaX < 0 &&
        this.session.getScrollLeft() >= 1 - this.scrollMargin.left
      )
        return true;
      if (
        deltaX > 0 &&
        this.session.getScrollLeft() +
          this.$size.scrollerWidth -
          this.layerConfig.width <
          -1 + this.scrollMargin.right
      )
        return true;
    };
    VirtualRenderer.prototype.pixelToScreenCoordinates = function (x, y) {
      var canvasPos;
      if (this.$hasCssTransforms) {
        canvasPos = { top: 0, left: 0 };
        var p = this.$fontMetrics.transformCoordinates([x, y]);
        x = p[1] - this.gutterWidth - this.margin.left;
        y = p[0];
      } else {
        canvasPos = this.scroller.getBoundingClientRect();
      }
      var offsetX = x + this.scrollLeft - canvasPos.left - this.$padding;
      var offset = offsetX / this.characterWidth;
      var row = Math.floor(
        (y + this.scrollTop - canvasPos.top) / this.lineHeight,
      );
      var col = this.$blockCursor ? Math.floor(offset) : Math.round(offset);
      return {
        row: row,
        column: col,
        side: offset - col > 0 ? 1 : -1,
        offsetX: offsetX,
      };
    };
    VirtualRenderer.prototype.screenToTextCoordinates = function (x, y) {
      var canvasPos;
      if (this.$hasCssTransforms) {
        canvasPos = { top: 0, left: 0 };
        var p = this.$fontMetrics.transformCoordinates([x, y]);
        x = p[1] - this.gutterWidth - this.margin.left;
        y = p[0];
      } else {
        canvasPos = this.scroller.getBoundingClientRect();
      }
      var offsetX = x + this.scrollLeft - canvasPos.left - this.$padding;
      var offset = offsetX / this.characterWidth;
      var col = this.$blockCursor ? Math.floor(offset) : Math.round(offset);
      var row = Math.floor(
        (y + this.scrollTop - canvasPos.top) / this.lineHeight,
      );
      return this.session.screenToDocumentPosition(
        row,
        Math.max(col, 0),
        offsetX,
      );
    };
    VirtualRenderer.prototype.textToScreenCoordinates = function (row, column) {
      var canvasPos = this.scroller.getBoundingClientRect();
      var pos = this.session.documentToScreenPosition(row, column);
      var x =
        this.$padding +
        (this.session.$bidiHandler.isBidiRow(pos.row, row)
          ? this.session.$bidiHandler.getPosLeft(pos.column)
          : Math.round(pos.column * this.characterWidth));
      var y = pos.row * this.lineHeight;
      return {
        pageX: canvasPos.left + x - this.scrollLeft,
        pageY: canvasPos.top + y - this.scrollTop,
      };
    };
    VirtualRenderer.prototype.visualizeFocus = function () {
      dom.addCssClass(this.container, "ace_focus");
    };
    VirtualRenderer.prototype.visualizeBlur = function () {
      dom.removeCssClass(this.container, "ace_focus");
    };
    VirtualRenderer.prototype.showComposition = function (composition) {
      this.$composition = composition;
      if (!composition.cssText) {
        composition.cssText = this.textarea.style.cssText;
      }
      if (composition.useTextareaForIME == undefined)
        composition.useTextareaForIME = this.$useTextareaForIME;
      if (this.$useTextareaForIME) {
        dom.addCssClass(this.textarea, "ace_composition");
        this.textarea.style.cssText = "";
        this.$moveTextAreaToCursor();
        this.$cursorLayer.element.style.display = "none";
      } else {
        composition.markerId = this.session.addMarker(
          composition.markerRange,
          "ace_composition_marker",
          "text",
        );
      }
    };
    VirtualRenderer.prototype.setCompositionText = function (text) {
      var cursor = this.session.selection.cursor;
      this.addToken(text, "composition_placeholder", cursor.row, cursor.column);
      this.$moveTextAreaToCursor();
    };
    VirtualRenderer.prototype.hideComposition = function () {
      if (!this.$composition) return;
      if (this.$composition.markerId)
        this.session.removeMarker(this.$composition.markerId);
      dom.removeCssClass(this.textarea, "ace_composition");
      this.textarea.style.cssText = this.$composition.cssText;
      var cursor = this.session.selection.cursor;
      this.removeExtraToken(cursor.row, cursor.column);
      this.$composition = null;
      this.$cursorLayer.element.style.display = "";
    };
    VirtualRenderer.prototype.setGhostText = function (text, position) {
      var cursor = this.session.selection.cursor;
      var insertPosition = position || {
        row: cursor.row,
        column: cursor.column,
      };
      this.removeGhostText();
      var textLines = text.split("\n");
      this.addToken(
        textLines[0],
        "ghost_text",
        insertPosition.row,
        insertPosition.column,
      );
      this.$ghostText = {
        text: text,
        position: {
          row: insertPosition.row,
          column: insertPosition.column,
        },
      };
      if (textLines.length > 1) {
        this.$ghostTextWidget = {
          text: textLines.slice(1).join("\n"),
          row: insertPosition.row,
          column: insertPosition.column,
          className: "ace_ghost_text",
        };
        this.session.widgetManager.addLineWidget(this.$ghostTextWidget);
        var pixelPosition = this.$cursorLayer.getPixelPosition(
          insertPosition,
          true,
        );
        var el = this.container;
        var height = el.getBoundingClientRect().height;
        var ghostTextHeight = textLines.length * this.lineHeight;
        var fitsY = ghostTextHeight < height - pixelPosition.top;
        if (fitsY) return;
        if (ghostTextHeight < height) {
          this.scrollBy(0, (textLines.length - 1) * this.lineHeight);
        } else {
          this.scrollBy(0, pixelPosition.top);
        }
      }
    };
    VirtualRenderer.prototype.removeGhostText = function () {
      if (!this.$ghostText) return;
      var position = this.$ghostText.position;
      this.removeExtraToken(position.row, position.column);
      if (this.$ghostTextWidget) {
        this.session.widgetManager.removeLineWidget(this.$ghostTextWidget);
        this.$ghostTextWidget = null;
      }
      this.$ghostText = null;
    };
    VirtualRenderer.prototype.addToken = function (text, type, row, column) {
      var session = this.session;
      session.bgTokenizer.lines[row] = null;
      var newToken = { type: type, value: text };
      var tokens = session.getTokens(row);
      if (column == null || !tokens.length) {
        tokens.push(newToken);
      } else {
        var l = 0;
        for (var i = 0; i < tokens.length; i++) {
          var token = tokens[i];
          l += token.value.length;
          if (column <= l) {
            var diff = token.value.length - (l - column);
            var before = token.value.slice(0, diff);
            var after = token.value.slice(diff);
            tokens.splice(i, 1, { type: token.type, value: before }, newToken, {
              type: token.type,
              value: after,
            });
            break;
          }
        }
      }
      this.updateLines(row, row);
    };
    VirtualRenderer.prototype.removeExtraToken = function (row, column) {
      this.session.bgTokenizer.lines[row] = null;
      this.updateLines(row, row);
    };
    VirtualRenderer.prototype.setTheme = function (theme, cb) {
      var _self = this;
      this.$themeId = theme;
      _self._dispatchEvent("themeChange", { theme: theme });
      if (!theme || typeof theme == "string") {
        var moduleName = theme || this.$options.theme.initialValue;
        config.loadModule(["theme", moduleName], afterLoad);
      } else {
        afterLoad(theme);
      }
      function afterLoad(module) {
        if (_self.$themeId != theme) return cb && cb();
        if (!module || !module.cssClass)
          throw new Error(
            "couldn't load module " + theme + " or it didn't call define",
          );
        if (module.$id) _self.$themeId = module.$id;
        dom.importCssString(module.cssText, module.cssClass, _self.container);
        if (_self.theme)
          dom.removeCssClass(_self.container, _self.theme.cssClass);
        var padding =
          "padding" in module
            ? module.padding
            : "padding" in (_self.theme || {})
              ? 4
              : _self.$padding;
        if (_self.$padding && padding != _self.$padding)
          _self.setPadding(padding);
        _self.$theme = module.cssClass;
        _self.theme = module;
        dom.addCssClass(_self.container, module.cssClass);
        dom.setCssClass(_self.container, "ace_dark", module.isDark);
        if (_self.$size) {
          _self.$size.width = 0;
          _self.$updateSizeAsync();
        }
        _self._dispatchEvent("themeLoaded", { theme: module });
        cb && cb();
      }
    };
    VirtualRenderer.prototype.getTheme = function () {
      return this.$themeId;
    };
    VirtualRenderer.prototype.setStyle = function (style, include) {
      dom.setCssClass(this.container, style, include !== false);
    };
    VirtualRenderer.prototype.unsetStyle = function (style) {
      dom.removeCssClass(this.container, style);
    };
    VirtualRenderer.prototype.setCursorStyle = function (style) {
      dom.setStyle(this.scroller.style, "cursor", style);
    };
    VirtualRenderer.prototype.setMouseCursor = function (cursorStyle) {
      dom.setStyle(this.scroller.style, "cursor", cursorStyle);
    };
    VirtualRenderer.prototype.attachToShadowRoot = function () {
      dom.importCssString(editorCss, "ace_editor.css", this.container);
    };
    VirtualRenderer.prototype.destroy = function () {
      this.freeze();
      this.$fontMetrics.destroy();
      this.$cursorLayer.destroy();
      this.removeAllListeners();
      this.container.textContent = "";
      this.setOption("useResizeObserver", false);
    };
    VirtualRenderer.prototype.$updateCustomScrollbar = function (val) {
      var _self = this;
      this.$horizScroll = this.$vScroll = null;
      this.scrollBarV.element.remove();
      this.scrollBarH.element.remove();
      if (this.$scrollDecorator) {
        delete this.$scrollDecorator;
      }
      if (val === true) {
        this.scrollBarV = new VScrollBarCustom(this.container, this);
        this.scrollBarH = new HScrollBarCustom(this.container, this);
        this.scrollBarV.setHeight(this.$size.scrollerHeight);
        this.scrollBarH.setWidth(this.$size.scrollerWidth);
        this.scrollBarV.addEventListener("scroll", function (e) {
          if (!_self.$scrollAnimation)
            _self.session.setScrollTop(e.data - _self.scrollMargin.top);
        });
        this.scrollBarH.addEventListener("scroll", function (e) {
          if (!_self.$scrollAnimation)
            _self.session.setScrollLeft(e.data - _self.scrollMargin.left);
        });
        this.$scrollDecorator = new Decorator(this.scrollBarV, this);
        this.$scrollDecorator.$updateDecorators();
      } else {
        this.scrollBarV = new VScrollBar(this.container, this);
        this.scrollBarH = new HScrollBar(this.container, this);
        this.scrollBarV.addEventListener("scroll", function (e) {
          if (!_self.$scrollAnimation)
            _self.session.setScrollTop(e.data - _self.scrollMargin.top);
        });
        this.scrollBarH.addEventListener("scroll", function (e) {
          if (!_self.$scrollAnimation)
            _self.session.setScrollLeft(e.data - _self.scrollMargin.left);
        });
      }
    };
    VirtualRenderer.prototype.$addResizeObserver = function () {
      if (!window.ResizeObserver || this.$resizeObserver) return;
      var self = this;
      this.$resizeTimer = lang.delayedCall(function () {
        if (!self.destroyed) self.onResize();
      }, 50);
      this.$resizeObserver = new window.ResizeObserver(function (e) {
        var w = e[0].contentRect.width;
        var h = e[0].contentRect.height;
        if (
          Math.abs(self.$size.width - w) > 1 ||
          Math.abs(self.$size.height - h) > 1
        ) {
          self.$resizeTimer.delay();
        } else {
          self.$resizeTimer.cancel();
        }
      });
      this.$resizeObserver.observe(this.container);
    };
    return VirtualRenderer;
  })();
  VirtualRenderer.prototype.CHANGE_CURSOR = 1;
  VirtualRenderer.prototype.CHANGE_MARKER = 2;
  VirtualRenderer.prototype.CHANGE_GUTTER = 4;
  VirtualRenderer.prototype.CHANGE_SCROLL = 8;
  VirtualRenderer.prototype.CHANGE_LINES = 16;
  VirtualRenderer.prototype.CHANGE_TEXT = 32;
  VirtualRenderer.prototype.CHANGE_SIZE = 64;
  VirtualRenderer.prototype.CHANGE_MARKER_BACK = 128;
  VirtualRenderer.prototype.CHANGE_MARKER_FRONT = 256;
  VirtualRenderer.prototype.CHANGE_FULL = 512;
  VirtualRenderer.prototype.CHANGE_H_SCROLL = 1024;
  VirtualRenderer.prototype.$changes = 0;
  VirtualRenderer.prototype.$padding = null;
  VirtualRenderer.prototype.$frozen = false;
  VirtualRenderer.prototype.STEPS = 8;
  oop.implement(VirtualRenderer.prototype, EventEmitter);
  config.defineOptions(VirtualRenderer.prototype, "renderer", {
    useResizeObserver: {
      set: function (value) {
        if (!value && this.$resizeObserver) {
          this.$resizeObserver.disconnect();
          this.$resizeTimer.cancel();
          this.$resizeTimer = this.$resizeObserver = null;
        } else if (value && !this.$resizeObserver) {
          this.$addResizeObserver();
        }
      },
    },
    animatedScroll: { initialValue: false },
    showInvisibles: {
      set: function (value) {
        if (this.$textLayer.setShowInvisibles(value))
          this.$loop.schedule(this.CHANGE_TEXT);
      },
      initialValue: false,
    },
    showPrintMargin: {
      set: function () {
        this.$updatePrintMargin();
      },
      initialValue: true,
    },
    printMarginColumn: {
      set: function () {
        this.$updatePrintMargin();
      },
      initialValue: 80,
    },
    printMargin: {
      set: function (val) {
        if (typeof val == "number") this.$printMarginColumn = val;
        this.$showPrintMargin = !!val;
        this.$updatePrintMargin();
      },
      get: function () {
        return this.$showPrintMargin && this.$printMarginColumn;
      },
    },
    showGutter: {
      set: function (show) {
        this.$gutter.style.display = show ? "block" : "none";
        this.$loop.schedule(this.CHANGE_FULL);
        this.onGutterResize();
      },
      initialValue: true,
    },
    useSvgGutterIcons: {
      set: function (value) {
        this.$gutterLayer.$useSvgGutterIcons = value;
      },
      initialValue: false,
    },
    showFoldedAnnotations: {
      set: function (value) {
        this.$gutterLayer.$showFoldedAnnotations = value;
      },
      initialValue: false,
    },
    fadeFoldWidgets: {
      set: function (show) {
        dom.setCssClass(this.$gutter, "ace_fade-fold-widgets", show);
      },
      initialValue: false,
    },
    showFoldWidgets: {
      set: function (show) {
        this.$gutterLayer.setShowFoldWidgets(show);
        this.$loop.schedule(this.CHANGE_GUTTER);
      },
      initialValue: true,
    },
    displayIndentGuides: {
      set: function (show) {
        if (this.$textLayer.setDisplayIndentGuides(show))
          this.$loop.schedule(this.CHANGE_TEXT);
      },
      initialValue: true,
    },
    highlightIndentGuides: {
      set: function (show) {
        if (this.$textLayer.setHighlightIndentGuides(show) == true) {
          this.$textLayer.$highlightIndentGuide();
        } else {
          this.$textLayer.$clearActiveIndentGuide(this.$textLayer.$lines.cells);
        }
      },
      initialValue: true,
    },
    highlightGutterLine: {
      set: function (shouldHighlight) {
        this.$gutterLayer.setHighlightGutterLine(shouldHighlight);
        this.$loop.schedule(this.CHANGE_GUTTER);
      },
      initialValue: true,
    },
    hScrollBarAlwaysVisible: {
      set: function (val) {
        if (!this.$hScrollBarAlwaysVisible || !this.$horizScroll)
          this.$loop.schedule(this.CHANGE_SCROLL);
      },
      initialValue: false,
    },
    vScrollBarAlwaysVisible: {
      set: function (val) {
        if (!this.$vScrollBarAlwaysVisible || !this.$vScroll)
          this.$loop.schedule(this.CHANGE_SCROLL);
      },
      initialValue: false,
    },
    fontSize: {
      set: function (size) {
        if (typeof size == "number") size = size + "px";
        this.container.style.fontSize = size;
        this.updateFontSize();
      },
      initialValue: 12,
    },
    fontFamily: {
      set: function (name) {
        this.container.style.fontFamily = name;
        this.updateFontSize();
      },
    },
    maxLines: {
      set: function (val) {
        this.updateFull();
      },
    },
    minLines: {
      set: function (val) {
        if (!(this.$minLines < 0x1ffffffffffff)) this.$minLines = 0;
        this.updateFull();
      },
    },
    maxPixelHeight: {
      set: function (val) {
        this.updateFull();
      },
      initialValue: 0,
    },
    scrollPastEnd: {
      set: function (val) {
        val = +val || 0;
        if (this.$scrollPastEnd == val) return;
        this.$scrollPastEnd = val;
        this.$loop.schedule(this.CHANGE_SCROLL);
      },
      initialValue: 0,
      handlesSet: true,
    },
    fixedWidthGutter: {
      set: function (val) {
        this.$gutterLayer.$fixedWidth = !!val;
        this.$loop.schedule(this.CHANGE_GUTTER);
      },
    },
    customScrollbar: {
      set: function (val) {
        this.$updateCustomScrollbar(val);
      },
      initialValue: false,
    },
    theme: {
      set: function (val) {
        this.setTheme(val);
      },
      get: function () {
        return this.$themeId || this.theme;
      },
      initialValue: "./theme/textmate",
      handlesSet: true,
    },
    hasCssTransforms: {},
    useTextareaForIME: {
      initialValue: !useragent.isMobile && !useragent.isIE,
    },
  });
  exports.VirtualRenderer = VirtualRenderer;
});

define("ace/worker/worker_client", [
  "require",
  "exports",
  "module",
  "ace/lib/oop",
  "ace/lib/net",
  "ace/lib/event_emitter",
  "ace/config",
], function (require, exports, module) {
  "use strict";

  var oop = require("../lib/oop");
  var net = require("../lib/net");
  var EventEmitter = require("../lib/event_emitter").EventEmitter;
  var config = require("../config");

  function $workerBlob(workerUrl) {
    var script = "importScripts('" + net.qualifyURL(workerUrl) + "');";
    try {
      return new Blob([script], { type: "application/javascript" });
    } catch (e) {
      // Backwards-compatibility
      var BlobBuilder =
        window.BlobBuilder || window.WebKitBlobBuilder || window.MozBlobBuilder;
      var blobBuilder = new BlobBuilder();
      blobBuilder.append(script);
      return blobBuilder.getBlob("application/javascript");
    }
  }

  function createWorker(workerUrl) {
    if (typeof Worker == "undefined")
      return { postMessage: function () {}, terminate: function () {} };
    if (config.get("loadWorkerFromBlob")) {
      var blob = $workerBlob(workerUrl);
      var URL = window.URL || window.webkitURL;
      var blobURL = URL.createObjectURL(blob);
      return new Worker(blobURL);
    }
    return new Worker(workerUrl);
  }

  var WorkerClient = function (worker) {
    if (!worker.postMessage)
      worker = this.$createWorkerFromOldConfig.apply(this, arguments);

    this.$worker = worker;
    this.$sendDeltaQueue = this.$sendDeltaQueue.bind(this);
    this.changeListener = this.changeListener.bind(this);
    this.onMessage = this.onMessage.bind(this);

    this.callbackId = 1;
    this.callbacks = {};

    this.$worker.onmessage = this.onMessage;
  };

  (function () {
    oop.implement(this, EventEmitter);

    this.$createWorkerFromOldConfig = function (
      topLevelNamespaces,
      mod,
      classname,
      workerUrl,
      importScripts,
    ) {
      if (require.nameToUrl && !require.toUrl)
        require.toUrl = require.nameToUrl;

      if (config.get("packaged") || !require.toUrl) {
        workerUrl = workerUrl || config.moduleUrl(mod, "worker");
      } else {
        var normalizePath = this.$normalizePath;
        workerUrl =
          workerUrl ||
          normalizePath(require.toUrl("ace/worker/worker.js", null, "_"));

        var tlns = {};
        topLevelNamespaces.forEach(function (ns) {
          tlns[ns] = normalizePath(
            require.toUrl(ns, null, "_").replace(/(\.js)?(\?.*)?$/, ""),
          );
        });
      }

      this.$worker = createWorker(workerUrl);
      if (importScripts) {
        this.send("importScripts", importScripts);
      }
      this.$worker.postMessage({
        init: true,
        tlns: tlns,
        module: mod,
        classname: classname,
      });
      return this.$worker;
    };

    this.onMessage = function (e) {
      var msg = e.data;
      switch (msg.type) {
        case "event":
          this._signal(msg.name, { data: msg.data });
          break;
        case "call":
          var callback = this.callbacks[msg.id];
          if (callback) {
            callback(msg.data);
            delete this.callbacks[msg.id];
          }
          break;
        case "error":
          this.reportError(msg.data);
          break;
        case "log":
          window.console && console.log && console.log.apply(console, msg.data);
          break;
      }
    };

    this.reportError = function (err) {
      window.console && console.error && console.error(err);
    };

    this.$normalizePath = function (path) {
      return net.qualifyURL(path);
    };

    this.terminate = function () {
      this._signal("terminate", {});
      this.deltaQueue = null;
      this.$worker.terminate();
      this.$worker.onerror = function (e) {
        e.preventDefault();
      };
      this.$worker = null;
      if (this.$doc) this.$doc.off("change", this.changeListener);
      this.$doc = null;
    };

    this.send = function (cmd, args) {
      this.$worker.postMessage({ command: cmd, args: args });
    };

    this.call = function (cmd, args, callback) {
      if (callback) {
        var id = this.callbackId++;
        this.callbacks[id] = callback;
        args.push(id);
      }
      this.send(cmd, args);
    };

    this.emit = function (event, data) {
      try {
        if (data.data && data.data.err)
          data.data.err = {
            message: data.data.err.message,
            stack: data.data.err.stack,
            code: data.data.err.code,
          };
        this.$worker &&
          this.$worker.postMessage({ event: event, data: { data: data.data } });
      } catch (ex) {
        console.error(ex.stack);
      }
    };

    this.attachToDocument = function (doc) {
      if (this.$doc) this.terminate();

      this.$doc = doc;
      this.call("setValue", [doc.getValue()]);
      doc.on("change", this.changeListener, true);
    };

    this.changeListener = function (delta) {
      if (!this.deltaQueue) {
        this.deltaQueue = [];
        setTimeout(this.$sendDeltaQueue, 0);
      }
      if (delta.action == "insert")
        this.deltaQueue.push(delta.start, delta.lines);
      else this.deltaQueue.push(delta.start, delta.end);
    };

    this.$sendDeltaQueue = function () {
      var q = this.deltaQueue;
      if (!q) return;
      this.deltaQueue = null;
      if (q.length > 50 && q.length > this.$doc.getLength() >> 1) {
        this.call("setValue", [this.$doc.getValue()]);
      } else this.emit("change", { data: q });
    };
  }).call(WorkerClient.prototype);

  var UIWorkerClient = function (topLevelNamespaces, mod, classname) {
    var main = null;
    var emitSync = false;
    var sender = Object.create(EventEmitter);

    var messageBuffer = [];
    var workerClient = new WorkerClient({
      messageBuffer: messageBuffer,
      terminate: function () {},
      postMessage: function (e) {
        messageBuffer.push(e);
        if (!main) return;
        if (emitSync) setTimeout(processNext);
        else processNext();
      },
    });

    workerClient.setEmitSync = function (val) {
      emitSync = val;
    };

    var processNext = function () {
      var msg = messageBuffer.shift();
      if (msg.command) main[msg.command].apply(main, msg.args);
      else if (msg.event) sender._signal(msg.event, msg.data);
    };

    sender.postMessage = function (msg) {
      workerClient.onMessage({ data: msg });
    };
    sender.callback = function (data, callbackId) {
      this.postMessage({ type: "call", id: callbackId, data: data });
    };
    sender.emit = function (name, data) {
      this.postMessage({ type: "event", name: name, data: data });
    };

    config.loadModule(["worker", mod], function (Main) {
      main = new Main[classname](sender);
      while (messageBuffer.length) processNext();
    });

    return workerClient;
  };

  exports.UIWorkerClient = UIWorkerClient;
  exports.WorkerClient = WorkerClient;
  exports.createWorker = createWorker;
});

define("ace/placeholder", [
  "require",
  "exports",
  "module",
  "ace/range",
  "ace/lib/event_emitter",
  "ace/lib/oop",
], function (require, exports, module) {
  "use strict";
  var Range = require("./range").Range;
  var EventEmitter = require("./lib/event_emitter").EventEmitter;
  var oop = require("./lib/oop");
  var PlaceHolder = /** @class */ (function () {
    function PlaceHolder(session, length, pos, others, mainClass, othersClass) {
      var _self = this;
      this.length = length;
      this.session = session;
      this.doc = session.getDocument();
      this.mainClass = mainClass;
      this.othersClass = othersClass;
      this.$onUpdate = this.onUpdate.bind(this);
      this.doc.on("change", this.$onUpdate, true);
      this.$others = others;
      this.$onCursorChange = function () {
        setTimeout(function () {
          _self.onCursorChange();
        });
      };
      this.$pos = pos;
      var undoStack = session.getUndoManager().$undoStack ||
        session.getUndoManager()["$undostack"] || { length: -1 };
      this.$undoStackDepth = undoStack.length;
      this.setup();
      session.selection.on("changeCursor", this.$onCursorChange);
    }
    PlaceHolder.prototype.setup = function () {
      var _self = this;
      var doc = this.doc;
      var session = this.session;
      this.selectionBefore = session.selection.toJSON();
      if (session.selection.inMultiSelectMode)
        session.selection.toSingleRange();
      this.pos = doc.createAnchor(this.$pos.row, this.$pos.column);
      var pos = this.pos;
      pos.$insertRight = true;
      pos.detach();
      pos.markerId = session.addMarker(
        new Range(pos.row, pos.column, pos.row, pos.column + this.length),
        this.mainClass,
        null,
        false,
      );
      this.others = [];
      this.$others.forEach(function (other) {
        var anchor = doc.createAnchor(other.row, other.column);
        anchor.$insertRight = true;
        anchor.detach();
        _self.others.push(anchor);
      });
      session.setUndoSelect(false);
    };
    PlaceHolder.prototype.showOtherMarkers = function () {
      if (this.othersActive) return;
      var session = this.session;
      var _self = this;
      this.othersActive = true;
      this.others.forEach(function (anchor) {
        anchor.markerId = session.addMarker(
          new Range(
            anchor.row,
            anchor.column,
            anchor.row,
            anchor.column + _self.length,
          ),
          _self.othersClass,
          null,
          false,
        );
      });
    };
    PlaceHolder.prototype.hideOtherMarkers = function () {
      if (!this.othersActive) return;
      this.othersActive = false;
      for (var i = 0; i < this.others.length; i++) {
        this.session.removeMarker(this.others[i].markerId);
      }
    };
    PlaceHolder.prototype.onUpdate = function (delta) {
      if (this.$updating) return this.updateAnchors(delta);
      var range = delta;
      if (range.start.row !== range.end.row) return;
      if (range.start.row !== this.pos.row) return;
      this.$updating = true;
      var lengthDiff =
        delta.action === "insert"
          ? range.end.column - range.start.column
          : range.start.column - range.end.column;
      var inMainRange =
        range.start.column >= this.pos.column &&
        range.start.column <= this.pos.column + this.length + 1;
      var distanceFromStart = range.start.column - this.pos.column;
      this.updateAnchors(delta);
      if (inMainRange) this.length += lengthDiff;
      if (inMainRange && !this.session.$fromUndo) {
        if (delta.action === "insert") {
          for (var i = this.others.length - 1; i >= 0; i--) {
            var otherPos = this.others[i];
            var newPos = {
              row: otherPos.row,
              column: otherPos.column + distanceFromStart,
            };
            this.doc.insertMergedLines(newPos, delta.lines);
          }
        } else if (delta.action === "remove") {
          for (var i = this.others.length - 1; i >= 0; i--) {
            var otherPos = this.others[i];
            var newPos = {
              row: otherPos.row,
              column: otherPos.column + distanceFromStart,
            };
            this.doc.remove(
              new Range(
                newPos.row,
                newPos.column,
                newPos.row,
                newPos.column - lengthDiff,
              ),
            );
          }
        }
      }
      this.$updating = false;
      this.updateMarkers();
    };
    PlaceHolder.prototype.updateAnchors = function (delta) {
      this.pos.onChange(delta);
      for (var i = this.others.length; i--; ) this.others[i].onChange(delta);
      this.updateMarkers();
    };
    PlaceHolder.prototype.updateMarkers = function () {
      if (this.$updating) return;
      var _self = this;
      var session = this.session;
      var updateMarker = function (pos, className) {
        session.removeMarker(pos.markerId);
        pos.markerId = session.addMarker(
          new Range(pos.row, pos.column, pos.row, pos.column + _self.length),
          className,
          null,
          false,
        );
      };
      updateMarker(this.pos, this.mainClass);
      for (var i = this.others.length; i--; )
        updateMarker(this.others[i], this.othersClass);
    };
    PlaceHolder.prototype.onCursorChange = function (event) {
      if (this.$updating || !this.session) return;
      var pos = this.session.selection.getCursor();
      if (
        pos.row === this.pos.row &&
        pos.column >= this.pos.column &&
        pos.column <= this.pos.column + this.length
      ) {
        this.showOtherMarkers();
        this._emit("cursorEnter", event);
      } else {
        this.hideOtherMarkers();
        this._emit("cursorLeave", event);
      }
    };
    PlaceHolder.prototype.detach = function () {
      this.session.removeMarker(this.pos && this.pos.markerId);
      this.hideOtherMarkers();
      this.doc.off("change", this.$onUpdate);
      this.session.selection.off("changeCursor", this.$onCursorChange);
      this.session.setUndoSelect(true);
      this.session = null;
    };
    PlaceHolder.prototype.cancel = function () {
      if (this.$undoStackDepth === -1) return;
      var undoManager = this.session.getUndoManager();
      var undosRequired =
        (undoManager.$undoStack || undoManager["$undostack"]).length -
        this.$undoStackDepth;
      for (var i = 0; i < undosRequired; i++) {
        undoManager.undo(this.session, true);
      }
      if (this.selectionBefore)
        this.session.selection.fromJSON(this.selectionBefore);
    };
    return PlaceHolder;
  })();
  oop.implement(PlaceHolder.prototype, EventEmitter);
  exports.PlaceHolder = PlaceHolder;
});

define("ace/mouse/multi_select_handler", [
  "require",
  "exports",
  "module",
  "ace/lib/event",
  "ace/lib/useragent",
], function (require, exports, module) {
  var event = require("../lib/event");
  var useragent = require("../lib/useragent");
  function isSamePoint(p1, p2) {
    return p1.row == p2.row && p1.column == p2.column;
  }
  function onMouseDown(e) {
    var ev = e.domEvent;
    var alt = ev.altKey;
    var shift = ev.shiftKey;
    var ctrl = ev.ctrlKey;
    var accel = e.getAccelKey();
    var button = e.getButton();
    if (ctrl && useragent.isMac) button = ev.button;
    if (e.editor.inMultiSelectMode && button == 2) {
      e.editor.textInput.onContextMenu(e.domEvent);
      return;
    }
    if (!ctrl && !alt && !accel) {
      if (button === 0 && e.editor.inMultiSelectMode)
        e.editor.exitMultiSelectMode();
      return;
    }
    if (button !== 0) return;
    var editor = e.editor;
    var selection = editor.selection;
    var isMultiSelect = editor.inMultiSelectMode;
    var pos = e.getDocumentPosition();
    var cursor = selection.getCursor();
    var inSelection =
      e.inSelection() || (selection.isEmpty() && isSamePoint(pos, cursor));
    var mouseX = e.x,
      mouseY = e.y;
    var onMouseSelection = function (e) {
      mouseX = e.clientX;
      mouseY = e.clientY;
    };
    var session = editor.session;
    var screenAnchor = editor.renderer.pixelToScreenCoordinates(mouseX, mouseY);
    var screenCursor = screenAnchor;
    var selectionMode;
    if (editor.$mouseHandler.$enableJumpToDef) {
      if ((ctrl && alt) || (accel && alt))
        selectionMode = shift ? "block" : "add";
      else if (alt && editor.$blockSelectEnabled) selectionMode = "block";
    } else {
      if (accel && !alt) {
        selectionMode = "add";
        if (!isMultiSelect && shift) return;
      } else if (alt && editor.$blockSelectEnabled) {
        selectionMode = "block";
      }
    }
    if (selectionMode && useragent.isMac && ev.ctrlKey) {
      editor.$mouseHandler.cancelContextMenu();
    }
    if (selectionMode == "add") {
      if (!isMultiSelect && inSelection) return; // dragging
      if (!isMultiSelect) {
        var range = selection.toOrientedRange();
        editor.addSelectionMarker(range);
      }
      var oldRange = selection.rangeList.rangeAtPoint(pos);
      editor.inVirtualSelectionMode = true;
      if (shift) {
        oldRange = null;
        range = selection.ranges[0] || range;
        editor.removeSelectionMarker(range);
      }
      editor.once("mouseup", function () {
        var tmpSel = selection.toOrientedRange();
        if (
          oldRange &&
          tmpSel.isEmpty() &&
          isSamePoint(oldRange.cursor, tmpSel.cursor)
        )
          selection.substractPoint(tmpSel.cursor);
        else {
          if (shift) {
            selection.substractPoint(range.cursor);
          } else if (range) {
            editor.removeSelectionMarker(range);
            selection.addRange(range);
          }
          selection.addRange(tmpSel);
        }
        editor.inVirtualSelectionMode = false;
      });
    } else if (selectionMode == "block") {
      e.stop();
      editor.inVirtualSelectionMode = true;
      var initialRange;
      var rectSel = [];
      var blockSelect = function () {
        var newCursor = editor.renderer.pixelToScreenCoordinates(
          mouseX,
          mouseY,
        );
        var cursor = session.screenToDocumentPosition(
          newCursor.row,
          newCursor.column,
          newCursor.offsetX,
        );
        if (
          isSamePoint(screenCursor, newCursor) &&
          isSamePoint(cursor, selection.lead)
        )
          return;
        screenCursor = newCursor;
        editor.selection.moveToPosition(cursor);
        editor.renderer.scrollCursorIntoView();
        editor.removeSelectionMarkers(rectSel);
        rectSel = selection.rectangularRangeBlock(screenCursor, screenAnchor);
        if (
          editor.$mouseHandler.$clickSelection &&
          rectSel.length == 1 &&
          rectSel[0].isEmpty()
        )
          rectSel[0] = editor.$mouseHandler.$clickSelection.clone();
        rectSel.forEach(editor.addSelectionMarker, editor);
        editor.updateSelectionMarkers();
      };
      if (isMultiSelect && !accel) {
        selection.toSingleRange();
      } else if (!isMultiSelect && accel) {
        initialRange = selection.toOrientedRange();
        editor.addSelectionMarker(initialRange);
      }
      if (shift)
        screenAnchor = session.documentToScreenPosition(selection.lead);
      else selection.moveToPosition(pos);
      screenCursor = { row: -1, column: -1 };
      var onMouseSelectionEnd = function (e) {
        blockSelect();
        clearInterval(timerId);
        editor.removeSelectionMarkers(rectSel);
        if (!rectSel.length) rectSel = [selection.toOrientedRange()];
        if (initialRange) {
          editor.removeSelectionMarker(initialRange);
          selection.toSingleRange(initialRange);
        }
        for (var i = 0; i < rectSel.length; i++) selection.addRange(rectSel[i]);
        editor.inVirtualSelectionMode = false;
        editor.$mouseHandler.$clickSelection = null;
      };
      var onSelectionInterval = blockSelect;
      event.capture(editor.container, onMouseSelection, onMouseSelectionEnd);
      var timerId = setInterval(function () {
        onSelectionInterval();
      }, 20);
      return e.preventDefault();
    }
  }
  exports.onMouseDown = onMouseDown;
});

define("ace/commands/multi_select_commands", [
  "require",
  "exports",
  "module",
  "ace/keyboard/hash_handler",
], function (require, exports, module) {
  /**
   * commands to enter multiselect mode
   * @type {import("../../ace-internal").Ace.Command[]}
   */
  exports.defaultCommands = [
    {
      name: "addCursorAbove",
      description: "Add cursor above",
      exec: function (editor) {
        editor.selectMoreLines(-1);
      },
      bindKey: { win: "Ctrl-Alt-Up", mac: "Ctrl-Alt-Up" },
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "addCursorBelow",
      description: "Add cursor below",
      exec: function (editor) {
        editor.selectMoreLines(1);
      },
      bindKey: { win: "Ctrl-Alt-Down", mac: "Ctrl-Alt-Down" },
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "addCursorAboveSkipCurrent",
      description: "Add cursor above (skip current)",
      exec: function (editor) {
        editor.selectMoreLines(-1, true);
      },
      bindKey: { win: "Ctrl-Alt-Shift-Up", mac: "Ctrl-Alt-Shift-Up" },
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "addCursorBelowSkipCurrent",
      description: "Add cursor below (skip current)",
      exec: function (editor) {
        editor.selectMoreLines(1, true);
      },
      bindKey: { win: "Ctrl-Alt-Shift-Down", mac: "Ctrl-Alt-Shift-Down" },
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selectMoreBefore",
      description: "Select more before",
      exec: function (editor) {
        editor.selectMore(-1);
      },
      bindKey: { win: "Ctrl-Alt-Left", mac: "Ctrl-Alt-Left" },
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selectMoreAfter",
      description: "Select more after",
      exec: function (editor) {
        editor.selectMore(1);
      },
      bindKey: { win: "Ctrl-Alt-Right", mac: "Ctrl-Alt-Right" },
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selectNextBefore",
      description: "Select next before",
      exec: function (editor) {
        editor.selectMore(-1, true);
      },
      bindKey: { win: "Ctrl-Alt-Shift-Left", mac: "Ctrl-Alt-Shift-Left" },
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "selectNextAfter",
      description: "Select next after",
      exec: function (editor) {
        editor.selectMore(1, true);
      },
      bindKey: { win: "Ctrl-Alt-Shift-Right", mac: "Ctrl-Alt-Shift-Right" },
      scrollIntoView: "cursor",
      readOnly: true,
    },
    {
      name: "toggleSplitSelectionIntoLines",
      description: "Split selection into lines",
      exec: function (editor) {
        if (editor.multiSelect.rangeCount > 1)
          editor.multiSelect.joinSelections();
        else editor.multiSelect.splitIntoLines();
      },
      bindKey: { win: "Ctrl-Alt-L", mac: "Ctrl-Alt-L" },
      readOnly: true,
    },
    {
      name: "splitSelectionIntoLines",
      description: "Split into lines",
      exec: function (editor) {
        editor.multiSelect.splitIntoLines();
      },
      readOnly: true,
    },
    {
      name: "alignCursors",
      description: "Align cursors",
      exec: function (editor) {
        editor.alignCursors();
      },
      bindKey: { win: "Ctrl-Alt-A", mac: "Ctrl-Alt-A" },
      scrollIntoView: "cursor",
    },
    {
      name: "findAll",
      description: "Find all",
      exec: function (editor) {
        editor.findAll();
      },
      bindKey: { win: "Ctrl-Alt-K", mac: "Ctrl-Alt-G" },
      scrollIntoView: "cursor",
      readOnly: true,
    },
  ];
  exports.multiSelectCommands = [
    {
      name: "singleSelection",
      description: "Single selection",
      bindKey: "esc",
      exec: function (editor) {
        editor.exitMultiSelectMode();
      },
      scrollIntoView: "cursor",
      readOnly: true,
      isAvailable: function (editor) {
        return editor && editor.inMultiSelectMode;
      },
    },
  ];
  var HashHandler = require("../keyboard/hash_handler").HashHandler;
  exports.keyboardHandler = new HashHandler(exports.multiSelectCommands);
});

define("ace/multi_select", [
  "require",
  "exports",
  "module",
  "ace/range_list",
  "ace/range",
  "ace/selection",
  "ace/mouse/multi_select_handler",
  "ace/lib/event",
  "ace/lib/lang",
  "ace/commands/multi_select_commands",
  "ace/search",
  "ace/edit_session",
  "ace/editor",
  "ace/config",
], function (require, exports, module) {
  /**
   * @typedef {import("./anchor").Anchor} Anchor
   * @typedef {import("../ace-internal").Ace.Point} Point
   * @typedef {import("../ace-internal").Ace.ScreenCoordinates} ScreenCoordinates
   */
  var RangeList = require("./range_list").RangeList;
  var Range = require("./range").Range;
  var Selection = require("./selection").Selection;
  var onMouseDown = require("./mouse/multi_select_handler").onMouseDown;
  var event = require("./lib/event");
  var lang = require("./lib/lang");
  var commands = require("./commands/multi_select_commands");
  exports.commands = commands.defaultCommands.concat(
    commands.multiSelectCommands,
  );
  var Search = require("./search").Search;
  var search = new Search();
  function find(session, needle, dir) {
    search.$options.wrap = true;
    search.$options.needle = needle;
    search.$options.backwards = dir == -1;
    return search.find(session);
  }
  var EditSession = require("./edit_session").EditSession;
  (function () {
    this.getSelectionMarkers = function () {
      return this.$selectionMarkers;
    };
  }).call(EditSession.prototype);
  (function () {
    this.ranges = null;
    this.rangeList = null;
    this.addRange = function (range, $blockChangeEvents) {
      if (!range) return;
      if (!this.inMultiSelectMode && this.rangeCount === 0) {
        var oldRange = this.toOrientedRange();
        this.rangeList.add(oldRange);
        this.rangeList.add(range);
        if (this.rangeList.ranges.length != 2) {
          this.rangeList.removeAll();
          return $blockChangeEvents || this.fromOrientedRange(range);
        }
        this.rangeList.removeAll();
        this.rangeList.add(oldRange);
        this.$onAddRange(oldRange);
      }
      if (!range.cursor) range.cursor = range.end;
      var removed = this.rangeList.add(range);
      this.$onAddRange(range);
      if (removed.length) this.$onRemoveRange(removed);
      if (this.rangeCount > 1 && !this.inMultiSelectMode) {
        this._signal("multiSelect");
        this.inMultiSelectMode = true;
        this.session.$undoSelect = false;
        this.rangeList.attach(this.session);
      }
      return $blockChangeEvents || this.fromOrientedRange(range);
    };
    this.toSingleRange = function (range) {
      range = range || this.ranges[0];
      var removed = this.rangeList.removeAll();
      if (removed.length) this.$onRemoveRange(removed);
      range && this.fromOrientedRange(range);
    };
    this.substractPoint = function (pos) {
      var removed = this.rangeList.substractPoint(pos);
      if (removed) {
        this.$onRemoveRange(removed);
        return removed[0];
      }
    };
    this.mergeOverlappingRanges = function () {
      var removed = this.rangeList.merge();
      if (removed.length) this.$onRemoveRange(removed);
    };
    this.$onAddRange = function (range) {
      this.rangeCount = this.rangeList.ranges.length;
      this.ranges.unshift(range);
      this._signal("addRange", { range: range });
    };
    this.$onRemoveRange = function (removed) {
      this.rangeCount = this.rangeList.ranges.length;
      if (this.rangeCount == 1 && this.inMultiSelectMode) {
        var lastRange = this.rangeList.ranges.pop();
        removed.push(lastRange);
        this.rangeCount = 0;
      }
      for (var i = removed.length; i--; ) {
        var index = this.ranges.indexOf(removed[i]);
        this.ranges.splice(index, 1);
      }
      this._signal("removeRange", { ranges: removed });
      if (this.rangeCount === 0 && this.inMultiSelectMode) {
        this.inMultiSelectMode = false;
        this._signal("singleSelect");
        this.session.$undoSelect = true;
        this.rangeList.detach(this.session);
      }
      lastRange = lastRange || this.ranges[0];
      if (lastRange && !lastRange.isEqual(this.getRange()))
        this.fromOrientedRange(lastRange);
    };
    this.$initRangeList = function () {
      if (this.rangeList) return;
      this.rangeList = new RangeList();
      this.ranges = [];
      this.rangeCount = 0;
    };
    this.getAllRanges = function () {
      return this.rangeCount
        ? this.rangeList.ranges.concat()
        : [this.getRange()];
    };
    this.splitIntoLines = function () {
      var ranges = this.ranges.length ? this.ranges : [this.getRange()];
      var newRanges = [];
      for (var i = 0; i < ranges.length; i++) {
        var range = ranges[i];
        var row = range.start.row;
        var endRow = range.end.row;
        if (row === endRow) {
          newRanges.push(range.clone());
        } else {
          newRanges.push(
            new Range(
              row,
              range.start.column,
              row,
              this.session.getLine(row).length,
            ),
          );
          while (++row < endRow) newRanges.push(this.getLineRange(row, true));
          newRanges.push(new Range(endRow, 0, endRow, range.end.column));
        }
        if (i == 0 && !this.isBackwards()) newRanges = newRanges.reverse();
      }
      this.toSingleRange();
      for (var i = newRanges.length; i--; ) this.addRange(newRanges[i]);
    };
    this.joinSelections = function () {
      var ranges = this.rangeList.ranges;
      var lastRange = ranges[ranges.length - 1];
      var range = Range.fromPoints(ranges[0].start, lastRange.end);
      this.toSingleRange();
      this.setSelectionRange(range, lastRange.cursor == lastRange.start);
    };
    this.toggleBlockSelection = function () {
      if (this.rangeCount > 1) {
        var ranges = this.rangeList.ranges;
        var lastRange = ranges[ranges.length - 1];
        var range = Range.fromPoints(ranges[0].start, lastRange.end);
        this.toSingleRange();
        this.setSelectionRange(range, lastRange.cursor == lastRange.start);
      } else {
        var cursor = this.session.documentToScreenPosition(this.cursor);
        var anchor = this.session.documentToScreenPosition(this.anchor);
        var rectSel = this.rectangularRangeBlock(cursor, anchor);
        rectSel.forEach(this.addRange, this);
      }
    };
    this.rectangularRangeBlock = function (
      screenCursor,
      screenAnchor,
      includeEmptyLines,
    ) {
      var rectSel = [];
      var xBackwards = screenCursor.column < screenAnchor.column;
      if (xBackwards) {
        var startColumn = screenCursor.column;
        var endColumn = screenAnchor.column;
        var startOffsetX = screenCursor.offsetX;
        var endOffsetX = screenAnchor.offsetX;
      } else {
        var startColumn = screenAnchor.column;
        var endColumn = screenCursor.column;
        var startOffsetX = screenAnchor.offsetX;
        var endOffsetX = screenCursor.offsetX;
      }
      var yBackwards = screenCursor.row < screenAnchor.row;
      if (yBackwards) {
        var startRow = screenCursor.row;
        var endRow = screenAnchor.row;
      } else {
        var startRow = screenAnchor.row;
        var endRow = screenCursor.row;
      }
      if (startColumn < 0) startColumn = 0;
      if (startRow < 0) startRow = 0;
      if (startRow == endRow) includeEmptyLines = true;
      var docEnd;
      for (var row = startRow; row <= endRow; row++) {
        var range = Range.fromPoints(
          this.session.screenToDocumentPosition(row, startColumn, startOffsetX),
          this.session.screenToDocumentPosition(row, endColumn, endOffsetX),
        );
        if (range.isEmpty()) {
          if (docEnd && isSamePoint(range.end, docEnd)) break;
          docEnd = range.end;
        }
        range.cursor = xBackwards ? range.start : range.end;
        rectSel.push(range);
      }
      if (yBackwards) rectSel.reverse();
      if (!includeEmptyLines) {
        var end = rectSel.length - 1;
        while (rectSel[end].isEmpty() && end > 0) end--;
        if (end > 0) {
          var start = 0;
          while (rectSel[start].isEmpty()) start++;
        }
        for (var i = end; i >= start; i--) {
          if (rectSel[i].isEmpty()) rectSel.splice(i, 1);
        }
      }
      return rectSel;
    };
  }).call(Selection.prototype);
  var Editor = require("./editor").Editor;
  (function () {
    this.updateSelectionMarkers = function () {
      this.renderer.updateCursor();
      this.renderer.updateBackMarkers();
    };
    this.addSelectionMarker = function (orientedRange) {
      if (!orientedRange.cursor) orientedRange.cursor = orientedRange.end;
      var style = this.getSelectionStyle();
      orientedRange.marker = this.session.addMarker(
        orientedRange,
        "ace_selection",
        style,
      );
      this.session.$selectionMarkers.push(orientedRange);
      this.session.selectionMarkerCount = this.session.$selectionMarkers.length;
      return orientedRange;
    };
    this.removeSelectionMarker = function (range) {
      if (!range.marker) return;
      this.session.removeMarker(range.marker);
      var index = this.session.$selectionMarkers.indexOf(range);
      if (index != -1) this.session.$selectionMarkers.splice(index, 1);
      this.session.selectionMarkerCount = this.session.$selectionMarkers.length;
    };
    this.removeSelectionMarkers = function (ranges) {
      var markerList = this.session.$selectionMarkers;
      for (var i = ranges.length; i--; ) {
        var range = ranges[i];
        if (!range.marker) continue;
        this.session.removeMarker(range.marker);
        var index = markerList.indexOf(range);
        if (index != -1) markerList.splice(index, 1);
      }
      this.session.selectionMarkerCount = markerList.length;
    };
    this.$onAddRange = function (e) {
      this.addSelectionMarker(e.range);
      this.renderer.updateCursor();
      this.renderer.updateBackMarkers();
    };
    this.$onRemoveRange = function (e) {
      this.removeSelectionMarkers(e.ranges);
      this.renderer.updateCursor();
      this.renderer.updateBackMarkers();
    };
    this.$onMultiSelect = function (e) {
      if (this.inMultiSelectMode) return;
      this.inMultiSelectMode = true;
      this.setStyle("ace_multiselect");
      this.keyBinding.addKeyboardHandler(commands.keyboardHandler);
      this.commands.setDefaultHandler("exec", this.$onMultiSelectExec);
      this.renderer.updateCursor();
      this.renderer.updateBackMarkers();
    };
    this.$onSingleSelect = function (e) {
      if (this.session.multiSelect.inVirtualMode) return;
      this.inMultiSelectMode = false;
      this.unsetStyle("ace_multiselect");
      this.keyBinding.removeKeyboardHandler(commands.keyboardHandler);
      this.commands.removeDefaultHandler("exec", this.$onMultiSelectExec);
      this.renderer.updateCursor();
      this.renderer.updateBackMarkers();
      this._emit("changeSelection");
    };
    this.$onMultiSelectExec = function (e) {
      var command = e.command;
      var editor = e.editor;
      if (!editor.multiSelect) return;
      if (!command.multiSelectAction) {
        var result = command.exec(editor, e.args || {});
        editor.multiSelect.addRange(editor.multiSelect.toOrientedRange());
        editor.multiSelect.mergeOverlappingRanges();
      } else if (command.multiSelectAction == "forEach") {
        result = editor.forEachSelection(command, e.args);
      } else if (command.multiSelectAction == "forEachLine") {
        result = editor.forEachSelection(command, e.args, true);
      } else if (command.multiSelectAction == "single") {
        editor.exitMultiSelectMode();
        result = command.exec(editor, e.args || {});
      } else {
        result = command.multiSelectAction(editor, e.args || {});
      }
      return result;
    };
    this.forEachSelection = function (cmd, args, options) {
      if (this.inVirtualSelectionMode) return;
      var keepOrder = options && options.keepOrder;
      var $byLines = options == true || (options && options.$byLines);
      var session = this.session;
      var selection = this.selection;
      var rangeList = selection.rangeList;
      var ranges = (keepOrder ? selection : rangeList).ranges;
      var result;
      if (!ranges.length)
        return cmd.exec ? cmd.exec(this, args || {}) : cmd(this, args || {});
      var reg = selection._eventRegistry;
      selection._eventRegistry = {};
      var tmpSel = new Selection(session);
      this.inVirtualSelectionMode = true;
      for (var i = ranges.length; i--; ) {
        if ($byLines) {
          while (i > 0 && ranges[i].start.row == ranges[i - 1].end.row) i--;
        }
        tmpSel.fromOrientedRange(ranges[i]);
        tmpSel.index = i;
        this.selection = session.selection = tmpSel;
        var cmdResult = cmd.exec
          ? cmd.exec(this, args || {})
          : cmd(this, args || {});
        if (!result && cmdResult !== undefined) result = cmdResult;
        tmpSel.toOrientedRange(ranges[i]);
      }
      tmpSel.detach();
      this.selection = session.selection = selection;
      this.inVirtualSelectionMode = false;
      selection._eventRegistry = reg;
      selection.mergeOverlappingRanges();
      if (selection.ranges[0]) selection.fromOrientedRange(selection.ranges[0]);
      var anim = this.renderer.$scrollAnimation;
      this.onCursorChange();
      this.onSelectionChange();
      if (anim && anim.from == anim.to)
        this.renderer.animateScrolling(anim.from);
      return result;
    };
    this.exitMultiSelectMode = function () {
      if (!this.inMultiSelectMode || this.inVirtualSelectionMode) return;
      this.multiSelect.toSingleRange();
    };
    this.getSelectedText = function () {
      var text = "";
      if (this.inMultiSelectMode && !this.inVirtualSelectionMode) {
        var ranges = this.multiSelect.rangeList.ranges;
        var buf = [];
        for (var i = 0; i < ranges.length; i++) {
          buf.push(this.session.getTextRange(ranges[i]));
        }
        var nl = this.session.getDocument().getNewLineCharacter();
        text = buf.join(nl);
        if (text.length == (buf.length - 1) * nl.length) text = "";
      } else if (!this.selection.isEmpty()) {
        text = this.session.getTextRange(this.getSelectionRange());
      }
      return text;
    };
    this.$checkMultiselectChange = function (e, anchor) {
      if (this.inMultiSelectMode && !this.inVirtualSelectionMode) {
        var range = this.multiSelect.ranges[0];
        if (this.multiSelect.isEmpty() && anchor == this.multiSelect.anchor)
          return;
        var pos =
          anchor == this.multiSelect.anchor
            ? range.cursor == range.start
              ? range.end
              : range.start
            : range.cursor;
        if (
          pos.row != anchor.row ||
          this.session.$clipPositionToDocument(pos.row, pos.column).column !=
            anchor.column
        )
          this.multiSelect.toSingleRange(this.multiSelect.toOrientedRange());
        else this.multiSelect.mergeOverlappingRanges();
      }
    };
    this.findAll = function (needle, options, additive) {
      options = options || {};
      options.needle = needle || options.needle;
      if (options.needle == undefined) {
        var range = this.selection.isEmpty()
          ? this.selection.getWordRange()
          : this.selection.getRange();
        options.needle = this.session.getTextRange(range);
      }
      this.$search.set(options);
      var ranges = this.$search.findAll(this.session);
      if (!ranges.length) return 0;
      var selection = this.multiSelect;
      if (!additive) selection.toSingleRange(ranges[0]);
      for (var i = ranges.length; i--; ) selection.addRange(ranges[i], true);
      if (range && selection.rangeList.rangeAtPoint(range.start))
        selection.addRange(range, true);
      return ranges.length;
    };
    this.selectMoreLines = function (dir, skip) {
      var range = this.selection.toOrientedRange();
      var isBackwards = range.cursor == range.end;
      var screenLead = this.session.documentToScreenPosition(range.cursor);
      if (this.selection.$desiredColumn)
        screenLead.column = this.selection.$desiredColumn;
      var lead = this.session.screenToDocumentPosition(
        screenLead.row + dir,
        screenLead.column,
      );
      if (!range.isEmpty()) {
        var screenAnchor = this.session.documentToScreenPosition(
          isBackwards ? range.end : range.start,
        );
        var anchor = this.session.screenToDocumentPosition(
          screenAnchor.row + dir,
          screenAnchor.column,
        );
      } else {
        var anchor = lead;
      }
      if (isBackwards) {
        var newRange = Range.fromPoints(lead, anchor);
        newRange.cursor = newRange.start;
      } else {
        var newRange = Range.fromPoints(anchor, lead);
        newRange.cursor = newRange.end;
      }
      newRange.desiredColumn = screenLead.column;
      if (!this.selection.inMultiSelectMode) {
        this.selection.addRange(range);
      } else {
        if (skip) var toRemove = range.cursor;
      }
      this.selection.addRange(newRange);
      if (toRemove) this.selection.substractPoint(toRemove);
    };
    this.transposeSelections = function (dir) {
      var session = this.session;
      var sel = session.multiSelect;
      var all = sel.ranges;
      for (var i = all.length; i--; ) {
        var range = all[i];
        if (range.isEmpty()) {
          var tmp_1 = session.getWordRange(range.start.row, range.start.column);
          range.start.row = tmp_1.start.row;
          range.start.column = tmp_1.start.column;
          range.end.row = tmp_1.end.row;
          range.end.column = tmp_1.end.column;
        }
      }
      sel.mergeOverlappingRanges();
      var words = [];
      for (var i = all.length; i--; ) {
        var range = all[i];
        words.unshift(session.getTextRange(range));
      }
      if (dir < 0) words.unshift(words.pop());
      else words.push(words.shift());
      for (var i = all.length; i--; ) {
        var range = all[i];
        var tmp = range.clone();
        session.replace(range, words[i]);
        range.start.row = tmp.start.row;
        range.start.column = tmp.start.column;
      }
      sel.fromOrientedRange(sel.ranges[0]);
    };
    this.selectMore = function (dir, skip, stopAtFirst) {
      var session = this.session;
      var sel = session.multiSelect;
      var range = sel.toOrientedRange();
      if (range.isEmpty()) {
        range = session.getWordRange(range.start.row, range.start.column);
        range.cursor = dir == -1 ? range.start : range.end;
        this.multiSelect.addRange(range);
        if (stopAtFirst) return;
      }
      var needle = session.getTextRange(range);
      var newRange = find(session, needle, dir);
      if (newRange) {
        newRange.cursor = dir == -1 ? newRange.start : newRange.end;
        this.session.unfold(newRange);
        this.multiSelect.addRange(newRange);
        this.renderer.scrollCursorIntoView(null, 0.5);
      }
      if (skip) this.multiSelect.substractPoint(range.cursor);
    };
    this.alignCursors = function () {
      var session = this.session;
      var sel = session.multiSelect;
      var ranges = sel.ranges;
      var row = -1;
      var sameRowRanges = ranges.filter(function (r) {
        if (r.cursor.row == row) return true;
        row = r.cursor.row;
      });
      if (!ranges.length || sameRowRanges.length == ranges.length - 1) {
        var range = this.selection.getRange();
        var fr = range.start.row,
          lr = range.end.row;
        var guessRange = fr == lr;
        if (guessRange) {
          var max = this.session.getLength();
          var line;
          do {
            line = this.session.getLine(lr);
          } while (/[=:]/.test(line) && ++lr < max);
          do {
            line = this.session.getLine(fr);
          } while (/[=:]/.test(line) && --fr > 0);
          if (fr < 0) fr = 0;
          if (lr >= max) lr = max - 1;
        }
        var lines = this.session.removeFullLines(fr, lr);
        lines = this.$reAlignText(lines, guessRange);
        this.session.insert({ row: fr, column: 0 }, lines.join("\n") + "\n");
        if (!guessRange) {
          range.start.column = 0;
          range.end.column = lines[lines.length - 1].length;
        }
        this.selection.setRange(range);
      } else {
        sameRowRanges.forEach(function (r) {
          sel.substractPoint(r.cursor);
        });
        var maxCol = 0;
        var minSpace = Infinity;
        var spaceOffsets = ranges.map(function (r) {
          var p = r.cursor;
          var line = session.getLine(p.row);
          var spaceOffset = line.substr(p.column).search(/\S/g);
          if (spaceOffset == -1) spaceOffset = 0;
          if (p.column > maxCol) maxCol = p.column;
          if (spaceOffset < minSpace) minSpace = spaceOffset;
          return spaceOffset;
        });
        ranges.forEach(function (r, i) {
          var p = r.cursor;
          var l = maxCol - p.column;
          var d = spaceOffsets[i] - minSpace;
          if (l > d) session.insert(p, lang.stringRepeat(" ", l - d));
          else
            session.remove(new Range(p.row, p.column, p.row, p.column - l + d));
          r.start.column = r.end.column = maxCol;
          r.start.row = r.end.row = p.row;
          r.cursor = r.end;
        });
        sel.fromOrientedRange(ranges[0]);
        this.renderer.updateCursor();
        this.renderer.updateBackMarkers();
      }
    };
    this.$reAlignText = function (lines, forceLeft) {
      var isLeftAligned = true,
        isRightAligned = true;
      var startW, textW, endW;
      return lines
        .map(function (line) {
          var m = line.match(/(\s*)(.*?)(\s*)([=:].*)/);
          if (!m) return [line];
          if (startW == null) {
            startW = m[1].length;
            textW = m[2].length;
            endW = m[3].length;
            return m;
          }
          if (startW + textW + endW != m[1].length + m[2].length + m[3].length)
            isRightAligned = false;
          if (startW != m[1].length) isLeftAligned = false;
          if (startW > m[1].length) startW = m[1].length;
          if (textW < m[2].length) textW = m[2].length;
          if (endW > m[3].length) endW = m[3].length;
          return m;
        })
        .map(
          forceLeft
            ? alignLeft
            : isLeftAligned
              ? isRightAligned
                ? alignRight
                : alignLeft
              : unAlign,
        );
      function spaces(n) {
        return lang.stringRepeat(" ", n);
      }
      function alignLeft(m) {
        return !m[2]
          ? m[0]
          : spaces(startW) +
              m[2] +
              spaces(textW - m[2].length + endW) +
              m[4].replace(/^([=:])\s+/, "$1 ");
      }
      function alignRight(m) {
        return !m[2]
          ? m[0]
          : spaces(startW + textW - m[2].length) +
              m[2] +
              spaces(endW) +
              m[4].replace(/^([=:])\s+/, "$1 ");
      }
      function unAlign(m) {
        return !m[2]
          ? m[0]
          : spaces(startW) +
              m[2] +
              spaces(endW) +
              m[4].replace(/^([=:])\s+/, "$1 ");
      }
    };
  }).call(Editor.prototype);
  function isSamePoint(p1, p2) {
    return p1.row == p2.row && p1.column == p2.column;
  }
  exports.onSessionChange = function (e) {
    var session = e.session;
    if (session && !session.multiSelect) {
      session.$selectionMarkers = [];
      session.selection.$initRangeList();
      session.multiSelect = session.selection;
    }
    this.multiSelect = session && session.multiSelect;
    var oldSession = e.oldSession;
    if (oldSession) {
      oldSession.multiSelect.off("addRange", this.$onAddRange);
      oldSession.multiSelect.off("removeRange", this.$onRemoveRange);
      oldSession.multiSelect.off("multiSelect", this.$onMultiSelect);
      oldSession.multiSelect.off("singleSelect", this.$onSingleSelect);
      oldSession.multiSelect.lead.off("change", this.$checkMultiselectChange);
      oldSession.multiSelect.anchor.off("change", this.$checkMultiselectChange);
    }
    if (session) {
      session.multiSelect.on("addRange", this.$onAddRange);
      session.multiSelect.on("removeRange", this.$onRemoveRange);
      session.multiSelect.on("multiSelect", this.$onMultiSelect);
      session.multiSelect.on("singleSelect", this.$onSingleSelect);
      session.multiSelect.lead.on("change", this.$checkMultiselectChange);
      session.multiSelect.anchor.on("change", this.$checkMultiselectChange);
    }
    if (
      session &&
      this.inMultiSelectMode != session.selection.inMultiSelectMode
    ) {
      if (session.selection.inMultiSelectMode) this.$onMultiSelect();
      else this.$onSingleSelect();
    }
  };
  function MultiSelect(editor) {
    if (editor.$multiselectOnSessionChange) return;
    editor.$onAddRange = editor.$onAddRange.bind(editor);
    editor.$onRemoveRange = editor.$onRemoveRange.bind(editor);
    editor.$onMultiSelect = editor.$onMultiSelect.bind(editor);
    editor.$onSingleSelect = editor.$onSingleSelect.bind(editor);
    editor.$multiselectOnSessionChange = exports.onSessionChange.bind(editor);
    editor.$checkMultiselectChange =
      editor.$checkMultiselectChange.bind(editor);
    editor.$multiselectOnSessionChange(editor);
    editor.on("changeSession", editor.$multiselectOnSessionChange);
    editor.on("mousedown", onMouseDown);
    editor.commands.addCommands(commands.defaultCommands);
    addAltCursorListeners(editor);
  }
  function addAltCursorListeners(editor) {
    if (!editor.textInput) return;
    var el = editor.textInput.getElement();
    var altCursor = false;
    event.addListener(
      el,
      "keydown",
      function (e) {
        var altDown =
          e.keyCode == 18 && !(e.ctrlKey || e.shiftKey || e.metaKey);
        if (editor.$blockSelectEnabled && altDown) {
          if (!altCursor) {
            editor.renderer.setMouseCursor("crosshair");
            altCursor = true;
          }
        } else if (altCursor) {
          reset();
        }
      },
      editor,
    );
    event.addListener(el, "keyup", reset, editor);
    event.addListener(el, "blur", reset, editor);
    function reset(e) {
      if (altCursor) {
        editor.renderer.setMouseCursor("");
        altCursor = false;
      }
    }
  }
  exports.MultiSelect = MultiSelect;
  require("./config").defineOptions(Editor.prototype, "editor", {
    enableMultiselect: {
      set: function (val) {
        MultiSelect(this);
        if (val) {
          this.on("mousedown", onMouseDown);
        } else {
          this.off("mousedown", onMouseDown);
        }
      },
      value: true,
    },
    enableBlockSelect: {
      set: function (val) {
        this.$blockSelectEnabled = val;
      },
      value: true,
    },
  });
});

define("ace/mode/folding/fold_mode", [
  "require",
  "exports",
  "module",
  "ace/range",
], function (require, exports, module) {
  "use strict";
  var Range = require("../../range").Range;
  var FoldMode = (exports.FoldMode = function () {});
  (function () {
    this.foldingStartMarker = null;
    this.foldingStopMarker = null;
    this.getFoldWidget = function (session, foldStyle, row) {
      var line = session.getLine(row);
      if (this.foldingStartMarker.test(line)) return "start";
      if (
        foldStyle == "markbeginend" &&
        this.foldingStopMarker &&
        this.foldingStopMarker.test(line)
      )
        return "end";
      return "";
    };
    this.getFoldWidgetRange = function (session, foldStyle, row) {
      return null;
    };
    this.indentationBlock = function (session, row, column) {
      var re = /\S/;
      var line = session.getLine(row);
      var startLevel = line.search(re);
      if (startLevel == -1) return;
      var startColumn = column || line.length;
      var maxRow = session.getLength();
      var startRow = row;
      var endRow = row;
      while (++row < maxRow) {
        var level = session.getLine(row).search(re);
        if (level == -1) continue;
        if (level <= startLevel) {
          var token = session.getTokenAt(row, 0);
          if (!token || token.type !== "string") break;
        }
        endRow = row;
      }
      if (endRow > startRow) {
        var endColumn = session.getLine(endRow).length;
        return new Range(startRow, startColumn, endRow, endColumn);
      }
    };
    this.openingBracketBlock = function (
      session,
      bracket,
      row,
      column,
      typeRe,
    ) {
      var start = { row: row, column: column + 1 };
      var end = session.$findClosingBracket(bracket, start, typeRe);
      if (!end) return;
      var fw = session.foldWidgets[end.row];
      if (fw == null) fw = session.getFoldWidget(end.row);
      if (fw == "start" && end.row > start.row) {
        end.row--;
        end.column = session.getLine(end.row).length;
      }
      return Range.fromPoints(start, end);
    };
    this.closingBracketBlock = function (
      session,
      bracket,
      row,
      column,
      typeRe,
    ) {
      var end = { row: row, column: column };
      var start = session.$findOpeningBracket(bracket, end);
      if (!start) return;
      start.column++;
      end.column--;
      return Range.fromPoints(start, end);
    };
  }).call(FoldMode.prototype);
});

define("ace/ext/error_marker", [
  "require",
  "exports",
  "module",
  "ace/line_widgets",
  "ace/lib/dom",
  "ace/range",
  "ace/config",
], function (require, exports, module) {
  "use strict";
  var LineWidgets = require("../line_widgets").LineWidgets;
  var dom = require("../lib/dom");
  var Range = require("../range").Range;
  var nls = require("../config").nls;
  function binarySearch(array, needle, comparator) {
    var first = 0;
    var last = array.length - 1;
    while (first <= last) {
      var mid = (first + last) >> 1;
      var c = comparator(needle, array[mid]);
      if (c > 0) first = mid + 1;
      else if (c < 0) last = mid - 1;
      else return mid;
    }
    return -(first + 1);
  }
  function findAnnotations(session, row, dir) {
    var annotations = session.getAnnotations().sort(Range.comparePoints);
    if (!annotations.length) return;
    var i = binarySearch(
      annotations,
      { row: row, column: -1 },
      Range.comparePoints,
    );
    if (i < 0) i = -i - 1;
    if (i >= annotations.length) i = dir > 0 ? 0 : annotations.length - 1;
    else if (i === 0 && dir < 0) i = annotations.length - 1;
    var annotation = annotations[i];
    if (!annotation || !dir) return;
    if (annotation.row === row) {
      do {
        annotation = annotations[(i += dir)];
      } while (annotation && annotation.row === row);
      if (!annotation) return annotations.slice();
    }
    var matched = [];
    row = annotation.row;
    do {
      matched[dir < 0 ? "unshift" : "push"](annotation);
      annotation = annotations[(i += dir)];
    } while (annotation && annotation.row == row);
    return matched.length && matched;
  }
  exports.showErrorMarker = function (editor, dir) {
    var session = editor.session;
    if (!session.widgetManager) {
      session.widgetManager = new LineWidgets(session);
      session.widgetManager.attach(editor);
    }
    var pos = editor.getCursorPosition();
    var row = pos.row;
    var oldWidget = session.widgetManager
      .getWidgetsAtRow(row)
      .filter(function (w) {
        return w.type == "errorMarker";
      })[0];
    if (oldWidget) {
      oldWidget.destroy();
    } else {
      row -= dir;
    }
    var annotations = findAnnotations(session, row, dir);
    var gutterAnno;
    if (annotations) {
      var annotation = annotations[0];
      pos.column =
        (annotation.pos && typeof annotation.column != "number"
          ? annotation.pos.sc
          : annotation.column) || 0;
      pos.row = annotation.row;
      gutterAnno = editor.renderer.$gutterLayer.$annotations[pos.row];
    } else if (oldWidget) {
      return;
    } else {
      gutterAnno = {
        text: [nls("Looks good!")],
        className: "ace_ok",
      };
    }
    editor.session.unfold(pos.row);
    editor.selection.moveToPosition(pos);
    var w = {
      row: pos.row,
      fixedWidth: true,
      coverGutter: true,
      el: dom.createElement("div"),
      type: "errorMarker",
    };
    var el = w.el.appendChild(dom.createElement("div"));
    var arrow = w.el.appendChild(dom.createElement("div"));
    arrow.className = "error_widget_arrow " + gutterAnno.className;
    var left = editor.renderer.$cursorLayer.getPixelPosition(pos).left;
    arrow.style.left = left + editor.renderer.gutterWidth - 5 + "px";
    w.el.className = "error_widget_wrapper";
    el.className = "error_widget " + gutterAnno.className;
    el.innerHTML = gutterAnno.text.join("<br>");
    el.appendChild(dom.createElement("div"));
    var kb = function (_, hashId, keyString) {
      if (hashId === 0 && (keyString === "esc" || keyString === "return")) {
        w.destroy();
        return { command: "null" };
      }
    };
    w.destroy = function () {
      if (editor.$mouseHandler.isMousePressed) return;
      editor.keyBinding.removeKeyboardHandler(kb);
      session.widgetManager.removeLineWidget(w);
      editor.off("changeSelection", w.destroy);
      editor.off("changeSession", w.destroy);
      editor.off("mouseup", w.destroy);
      editor.off("change", w.destroy);
    };
    editor.keyBinding.addKeyboardHandler(kb);
    editor.on("changeSelection", w.destroy);
    editor.on("changeSession", w.destroy);
    editor.on("mouseup", w.destroy);
    editor.on("change", w.destroy);
    editor.session.widgetManager.addLineWidget(w);
    w.el.onmousedown = editor.focus.bind(editor);
    editor.renderer.scrollCursorIntoView(null, 0.5, {
      bottom: w.el.offsetHeight,
    });
  };
  dom.importCssString(
    "\n    .error_widget_wrapper {\n        background: inherit;\n        color: inherit;\n        border:none\n    }\n    .error_widget {\n        border-top: solid 2px;\n        border-bottom: solid 2px;\n        margin: 5px 0;\n        padding: 10px 40px;\n        white-space: pre-wrap;\n    }\n    .error_widget.ace_error, .error_widget_arrow.ace_error{\n        border-color: #ff5a5a\n    }\n    .error_widget.ace_warning, .error_widget_arrow.ace_warning{\n        border-color: #F1D817\n    }\n    .error_widget.ace_info, .error_widget_arrow.ace_info{\n        border-color: #5a5a5a\n    }\n    .error_widget.ace_ok, .error_widget_arrow.ace_ok{\n        border-color: #5aaa5a\n    }\n    .error_widget_arrow {\n        position: absolute;\n        border: solid 5px;\n        border-top-color: transparent!important;\n        border-right-color: transparent!important;\n        border-left-color: transparent!important;\n        top: -5px;\n    }\n",
    "error_marker.css",
    false,
  );
});

define("ace/ace", [
  "require",
  "exports",
  "module",
  "ace/lib/dom",
  "ace/range",
  "ace/editor",
  "ace/edit_session",
  "ace/undomanager",
  "ace/virtual_renderer",
  "ace/worker/worker_client",
  "ace/keyboard/hash_handler",
  "ace/placeholder",
  "ace/multi_select",
  "ace/mode/folding/fold_mode",
  "ace/theme/textmate",
  "ace/ext/error_marker",
  "ace/config",
  "ace/loader_build",
], function (require, exports, module) {
  /**
   * The main class required to set up an Ace instance in the browser.
   *
   * @namespace Ace
   **/
  "use strict";
  require("./loader_build")(exports);
  var dom = require("./lib/dom");
  var Range = require("./range").Range;
  var Editor = require("./editor").Editor;
  var EditSession = require("./edit_session").EditSession;
  var UndoManager = require("./undomanager").UndoManager;
  var Renderer = require("./virtual_renderer").VirtualRenderer;
  require("./worker/worker_client");
  require("./keyboard/hash_handler");
  require("./placeholder");
  require("./multi_select");
  require("./mode/folding/fold_mode");
  require("./theme/textmate");
  require("./ext/error_marker");
  exports.config = require("./config");
  exports.edit = function (el, options) {
    if (typeof el == "string") {
      var _id = el;
      el = document.getElementById(_id);
      if (!el) throw new Error("ace.edit can't find div #" + _id);
    }
    if (el && el.env && el.env.editor instanceof Editor) return el.env.editor;
    var value = "";
    if (el && /input|textarea/i.test(el.tagName)) {
      var oldNode = el;
      value = oldNode.value;
      el = dom.createElement("pre");
      oldNode.parentNode.replaceChild(el, oldNode);
    } else if (el) {
      value = el.textContent;
      el.innerHTML = "";
    }
    var doc = exports.createEditSession(value);
    var editor = new Editor(new Renderer(el), doc, options);
    var env = {
      document: doc,
      editor: editor,
      onResize: editor.resize.bind(editor, null),
    };
    if (oldNode) env.textarea = oldNode;
    editor.on("destroy", function () {
      env.editor.container.env = null; // prevent memory leak on old ie
    });
    editor.container.env = editor.env = env;
    return editor;
  };
  exports.createEditSession = function (text, mode) {
    var doc = new EditSession(text, mode);
    doc.setUndoManager(new UndoManager());
    return doc;
  };
  exports.Range = Range;
  exports.Editor = Editor;
  exports.EditSession = EditSession;
  exports.UndoManager = UndoManager;
  exports.VirtualRenderer = Renderer;
  exports.version = exports.config.version;
});
(function () {
  window.require(["ace/ace"], function (a) {
    if (a) {
      a.config.init(true);
      a.define = window.define;
    }
    var global = (function () {
      return this;
    })();
    if (!global && typeof window != "undefined") global = window; // can happen in strict mode
    if (!global && typeof self != "undefined") global = self; // can happen in webworker

    if (!global.ace) global.ace = a;
    for (var key in a) if (a.hasOwnProperty(key)) global.ace[key] = a[key];
    global.ace["default"] = global.ace;
    if (typeof module == "object" && typeof exports == "object" && module) {
      module.exports = global.ace;
    }
  });
})();
