define(['jquery'], function ($) {
  if (!Array.prototype.reduce) {
    /**
     * Array.prototype.reduce polyfill
     *
     * @param {Function} callback
     * @param {Value} [initialValue]
     * @return {Value}
     *
     * @see http://goo.gl/WNriQD
     */
    Array.prototype.reduce = function (callback) {
      var t = Object(this), len = t.length >>> 0, k = 0, value;
      if (arguments.length === 2) {
        value = arguments[1];
      } else {
        while (k < len && !(k in t)) {
          k++;
        }
        if (k >= len) {
          throw new TypeError('Reduce of empty array with no initial value');
        }
        value = t[k++];
      }
      for (; k < len; k++) {
        if (k in t) {
          value = callback(value, t[k], k, t);
        }
      }
      return value;
    };
  }

  if ('function' !== typeof Array.prototype.filter) {
    /**
     * Array.prototype.filter polyfill
     *
     * @param {Function} func
     * @return {Array}
     *
     * @see http://goo.gl/T1KFnq
     */
    Array.prototype.filter = function (func) {
      var t = Object(this), len = t.length >>> 0;

      var res = [];
      var thisArg = arguments.length >= 2 ? arguments[1] : void 0;
      for (var i = 0; i < len; i++) {
        if (i in t) {
          var val = t[i];
          if (func.call(thisArg, val, i, t)) {
            res.push(val);
          }
        }
      }
  
      return res;
    };
  }

  if (!Array.prototype.map) {
    /**
     * Array.prototype.map polyfill
     *
     * @param {Function} callback
     * @return {Array}
     *
     * @see https://goo.gl/SMWaMK
     */
    Array.prototype.map = function (callback, thisArg) {
      var T, A, k;
      if (this === null) {
        throw new TypeError(' this is null or not defined');
      }

      var O = Object(this);
      var len = O.length >>> 0;
      if (typeof callback !== 'function') {
        throw new TypeError(callback + ' is not a function');
      }
  
      if (arguments.length > 1) {
        T = thisArg;
      }
  
      A = new Array(len);
      k = 0;
  
      while (k < len) {
        var kValue, mappedValue;
        if (k in O) {
          kValue = O[k];
          mappedValue = callback.call(T, kValue, k, O);
          A[k] = mappedValue;
        }
        k++;
      }
      return A;
    };
  }

  var isSupportAmd = typeof define === 'function' && define.amd;

  /**
   * returns whether font is installed or not.
   *
   * @param {String} fontName
   * @return {Boolean}
   */
  var isFontInstalled = function (fontName) {
    var testFontName = fontName === 'Comic Sans MS' ? 'Courier New' : 'Comic Sans MS';
    var $tester = $('<div>').css({
      position: 'absolute',
      left: '-9999px',
      top: '-9999px',
      fontSize: '200px'
    }).text('mmmmmmmmmwwwwwww').appendTo(document.body);

    var originalWidth = $tester.css('fontFamily', testFontName).width();
    var width = $tester.css('fontFamily', fontName + ',' + testFontName).width();

    $tester.remove();

    return originalWidth !== width;
  };

  var userAgent = navigator.userAgent;
  var isMSIE = /MSIE|Trident/i.test(userAgent);
  var browserVersion;
  if (isMSIE) {
    var matches = /MSIE (\d+[.]\d+)/.exec(userAgent);
    if (matches) {
      browserVersion = parseFloat(matches[1]);
    }
    matches = /Trident\/.*rv:([0-9]{1,}[\.0-9]{0,})/.exec(userAgent);
    if (matches) {
      browserVersion = parseFloat(matches[1]);
    }
  }

  /**
   * @class core.agent
   *
   * Object which check platform and agent
   *
   * @singleton
   * @alternateClassName agent
   */
  var agent = {
    /** @property {Boolean} [isMac=false] true if this agent is Mac  */
    isMac: navigator.appVersion.indexOf('Mac') > -1,
    /** @property {Boolean} [isMSIE=false] true if this agent is a Internet Explorer  */
    isMSIE: isMSIE,
    /** @property {Boolean} [isFF=false] true if this agent is a Firefox  */
    isFF: /firefox/i.test(userAgent),
    isWebkit: /webkit/i.test(userAgent),
    /** @property {Boolean} [isSafari=false] true if this agent is a Safari  */
    isSafari: /safari/i.test(userAgent),
    /** @property {Float} browserVersion current browser version  */
    browserVersion: browserVersion,
    /** @property {String} jqueryVersion current jQuery version string  */
    jqueryVersion: parseFloat($.fn.jquery),
    isSupportAmd: isSupportAmd,
    hasCodeMirror: isSupportAmd ? require.specified('CodeMirror') : !!window.CodeMirror,
    isFontInstalled: isFontInstalled,
    isW3CRangeSupport: !!document.createRange
  };

  return agent;
});
