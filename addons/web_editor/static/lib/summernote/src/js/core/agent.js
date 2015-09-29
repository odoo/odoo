define(['jquery'], function ($) {
  if ('function' !== typeof Array.prototype.reduce) {
    /**
     * Array.prototype.reduce fallback
     *
     * https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/Reduce
     */
    Array.prototype.reduce = function (callback, optInitialValue) {
      var idx, value, length = this.length >>> 0, isValueSet = false;
      if (1 < arguments.length) {
        value = optInitialValue;
        isValueSet = true;
      }
      for (idx = 0; length > idx; ++idx) {
        if (this.hasOwnProperty(idx)) {
          if (isValueSet) {
            value = callback(value, this[idx], idx, this);
          } else {
            value = this[idx];
            isValueSet = true;
          }
        }
      }
      if (!isValueSet) {
        throw new TypeError('Reduce of empty array with no initial value');
      }
      return value;
    };
  }

  if ('function' !== typeof Array.prototype.filter) {
    Array.prototype.filter = function (fun/*, thisArg*/) {
      if (this === void 0 || this === null) {
        throw new TypeError();
      }
  
      var t = Object(this);
      var len = t.length >>> 0;
      if (typeof fun !== 'function') {
        throw new TypeError();
      }
  
      var res = [];
      var thisArg = arguments.length >= 2 ? arguments[1] : void 0;
      for (var i = 0; i < len; i++) {
        if (i in t) {
          var val = t[i];
          if (fun.call(thisArg, val, i, t)) {
            res.push(val);
          }
        }
      }
  
      return res;
    };
  }

  var isSupportAmd = typeof define === 'function' && define.amd;

  /**
   * returns whether font is installed or not.
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

  /**
   * Object which check platform and agent
   */
  var agent = {
    isMac: navigator.appVersion.indexOf('Mac') > -1,
    isMSIE: navigator.userAgent.indexOf('MSIE') > -1 || navigator.userAgent.indexOf('Trident') > -1,
    isFF: navigator.userAgent.indexOf('Firefox') > -1,
    jqueryVersion: parseFloat($.fn.jquery),
    isSupportAmd: isSupportAmd,
    hasCodeMirror: isSupportAmd ? require.specified('CodeMirror') : !!window.CodeMirror,
    isFontInstalled: isFontInstalled,
    isW3CRangeSupport: !!document.createRange
  };

  return agent;
});
