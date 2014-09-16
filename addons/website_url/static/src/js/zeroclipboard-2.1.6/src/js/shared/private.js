/**
 * Convert an `arguments` object into an Array.
 *
 * @returns The arguments as an Array
 * @private
 */
var _args = function(argumentsObj) {
  return _slice.call(argumentsObj, 0);
};


/**
 * Shallow-copy the owned, enumerable properties of one object over to another, similar to jQuery's `$.extend`.
 *
 * @returns The target object, augmented
 * @private
 */
var _extend = function() {
  var i, len, arg, prop, src, copy,
      args = _args(arguments),
      target = args[0] || {};

  for (i = 1, len = args.length; i < len; i++) {
    // Only deal with non-null/undefined values
    if ((arg = args[i]) != null) {
      // Extend the base object
      for (prop in arg) {
        if (_hasOwn.call(arg, prop)) {
          src = target[prop];
          copy = arg[prop];

          // Prevent never-ending loops and copying `undefined` valeus
          if (target !== copy && copy !== undefined) {
            target[prop] = copy;
          }
        }
      }
    }
  }
  return target;
};


/**
 * Return a deep copy of the source object or array.
 *
 * @returns Object or Array
 * @private
 */
var _deepCopy = function(source) {
  var copy, i, len, prop;

  // If not a non-null object, just return the original
  if (typeof source !== "object" || source == null) {
    copy = source;
  }
  // If an Array, iterate and recurse
  else if (typeof source.length === "number") {
    copy = [];
    for (i = 0, len = source.length; i < len; i++) {
      // Skip empty indices in sparse arrays
      if (_hasOwn.call(source, i)) {
        // Recurse
        copy[i] = _deepCopy(source[i]);
      }
    }
  }
  // If an Object, enumerate and recurse
  else {
    copy = {};
    for (prop in source) {
      // Skip prototype properties
      if (_hasOwn.call(source, prop)) {
        copy[prop] = _deepCopy(source[prop]);
      }
    }    
  }

  return copy;
};


/**
 * Makes a shallow copy of `obj` (like `_extend`) but filters its properties based on a list of `keys` to keep.
 * The inverse of `_omit`, mostly. The big difference is that these properties do NOT need to be enumerable to
 * be kept.
 *
 * @returns A new filtered object.
 * @private
 */
var _pick = function(obj, keys) {
  var newObj = {};
  for (var i = 0, len = keys.length; i < len; i++) {
    if (keys[i] in obj) {
      newObj[keys[i]] = obj[keys[i]];
    }
  }
  return newObj;
};


/**
 * Makes a shallow copy of `obj` (like `_extend`) but filters its properties based on a list of `keys` to omit.
 * The inverse of `_pick`.
 *
 * @returns A new filtered object.
 * @private
 */
var _omit = function(obj, keys) {
  var newObj = {};
  for (var prop in obj) {
    if (keys.indexOf(prop) === -1) {
      newObj[prop] = obj[prop];
    }
  }
  return newObj;
};


/**
 * Remove all owned, enumerable properties from an object.
 *
 * @returns The original object without its owned, enumerable properties.
 * @private
 */
var _deleteOwnProperties = function(obj) {
  if (obj) {
    for (var prop in obj) {
      if (_hasOwn.call(obj, prop)) {
        delete obj[prop];
      }
    }
  }
  return obj;
};


/**
 * Determine if an element is contained within another element.
 *
 * @returns Boolean
 * @private
 */
var _containedBy = function(el, ancestorEl) {
  if (
    el && el.nodeType === 1 && el.ownerDocument &&
    ancestorEl && (
      (ancestorEl.nodeType === 1 && ancestorEl.ownerDocument && ancestorEl.ownerDocument === el.ownerDocument) ||
      (ancestorEl.nodeType === 9 && !ancestorEl.ownerDocument && ancestorEl === el.ownerDocument)
    )
  ) {
    do {
      if (el === ancestorEl) {
        return true;
      }
      el = el.parentNode;
    }
    while (el);
  }

  return false;
};


/**
 * Get the URL path's parent directory.
 *
 * @returns String or `undefined`
 * @private
 */
var _getDirPathOfUrl = function(url) {
  var dir;
  if (typeof url === "string" && url) {
    dir = url.split("#")[0].split("?")[0];
    dir = url.slice(0, url.lastIndexOf("/") + 1);
  }
  return dir;
};


/**
 * Get the current script's URL by throwing an `Error` and analyzing it.
 *
 * @returns String or `undefined`
 * @private
 */
var _getCurrentScriptUrlFromErrorStack = function(stack) {
  var url, matches;
  if (typeof stack === "string" && stack) {
    matches = stack.match(/^(?:|[^:@]*@|.+\)@(?=http[s]?|file)|.+?\s+(?: at |@)(?:[^:\(]+ )*[\(]?)((?:http[s]?|file):\/\/[\/]?.+?\/[^:\)]*?)(?::\d+)(?::\d+)?/);
    if (matches && matches[1]) {
      url = matches[1];
    }
    else {
      matches = stack.match(/\)@((?:http[s]?|file):\/\/[\/]?.+?\/[^:\)]*?)(?::\d+)(?::\d+)?/);
      if (matches && matches[1]) {
        url = matches[1];
      }
    }
  }
  return url;
};


/**
 * Get the current script's URL by throwing an `Error` and analyzing it.
 *
 * @returns String or `undefined`
 * @private
 */
var _getCurrentScriptUrlFromError = function() {
  /*jshint newcap:false */
  var url, err;
  try {
    throw new _Error();
  }
  catch (e) {
    err = e;
  }

  if (err) {
    url = err.sourceURL || err.fileName || _getCurrentScriptUrlFromErrorStack(err.stack);
  }
  return url;
};


/**
 * Get the current script's URL.
 *
 * @returns String or `undefined`
 * @private
 */
var _getCurrentScriptUrl = function() {
  var jsPath, scripts, i;

  // Try to leverage the `currentScript` feature
  if (_document.currentScript && (jsPath = _document.currentScript.src)) {
    return jsPath;
  }

  // If it it not available, then seek the script out instead...
  scripts = _document.getElementsByTagName("script");

  // If there is only one script
  if (scripts.length === 1) {
    return scripts[0].src || undefined;
  }

  // If `script` elements have the `readyState` property in this browser
  if ("readyState" in scripts[0]) {
    for (i = scripts.length; i--; ) {
      if (scripts[i].readyState === "interactive" && (jsPath = scripts[i].src)) {
        return jsPath;
      }
    }
  }

  // If the document is still parsing, then the last script in the document is the one that is currently loading
  if (_document.readyState === "loading" && (jsPath = scripts[scripts.length - 1].src)) {
    return jsPath;
  }

  // Else take more drastic measures...
  if ((jsPath = _getCurrentScriptUrlFromError())) {
    return jsPath;
  }

  // Otherwise we cannot reliably know which exact script is executing....
  return undefined;
};


/**
 * Get the unanimous parent directory of ALL script tags.
 * If any script tags are either (a) inline or (b) from differing parent
 * directories, this method must return `undefined`.
 *
 * @returns String or `undefined`
 * @private
 */
var _getUnanimousScriptParentDir = function() {
  var i, jsDir, jsPath,
      scripts = _document.getElementsByTagName("script");

  // If every `script` has a `src` attribute AND they all come from the same directory
  for (i = scripts.length; i--; ) {
    if (!(jsPath = scripts[i].src)) {
      jsDir = null;
      break;
    }
    jsPath = _getDirPathOfUrl(jsPath);
    if (jsDir == null) {
      jsDir = jsPath;
    }
    else if (jsDir !== jsPath) {
      jsDir = null;
      break;
    }
  }

  // Otherwise we cannot reliably know what script is executing....
  return jsDir || undefined;
};


/**
 * Get the presumed location of the "ZeroClipboard.swf" file, based on the location
 * of the executing JavaScript file (e.g. "ZeroClipboard.js", etc.).
 *
 * @returns String
 * @private
 */
var _getDefaultSwfPath = function() {
  var jsDir = _getDirPathOfUrl(_getCurrentScriptUrl()) || _getUnanimousScriptParentDir() || "";
  return jsDir + "ZeroClipboard.swf";
};
