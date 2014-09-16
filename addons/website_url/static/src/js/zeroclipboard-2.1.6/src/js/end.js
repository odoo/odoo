

// The AMDJS logic branch is evaluated first to avoid potential confusion over
// the CommonJS syntactical sugar offered by AMD.
if (typeof define === "function" && define.amd) {
  define(function() {
    return ZeroClipboard;
  });
}
else if (typeof module === "object" && module && typeof module.exports === "object" && module.exports) {
  // CommonJS module loaders....
  module.exports = ZeroClipboard;
}
else {
  window.ZeroClipboard = ZeroClipboard;
}

})((function() {
  /*jshint strict: false */
  return this || window;
})());
