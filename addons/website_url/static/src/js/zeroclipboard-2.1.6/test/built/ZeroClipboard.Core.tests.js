/*global ZeroClipboard */

(function(module, test) {
  "use strict";

  // Helper functions
  var TestUtils = {
    getHtmlBridge: function() {
      return document.getElementById(ZeroClipboard.config("containerId"));
    }
  };

  var originalConfig, originalFlashDetect;


  module("ZeroClipboard.Core.js (built) unit tests", {
    setup: function() {
      // Store
      originalConfig = ZeroClipboard.config();
      originalFlashDetect = ZeroClipboard.isFlashUnusable;
      // Modify
      ZeroClipboard.isFlashUnusable = function() {
        return false;
      };
    },
    teardown: function() {
      // Restore
      ZeroClipboard.destroy();
      ZeroClipboard.config(originalConfig);
      ZeroClipboard.isFlashUnusable = originalFlashDetect;
    }
  });


  test("`swfPath` finds the expected default URL", function(assert) {
    assert.expect(1);

    // Assert, act, assert
    var rootOrigin = window.location.protocol + "//" + window.location.host + "/";
    var indexOfTest = window.location.pathname.toLowerCase().indexOf("/test/");
    var rootDir = window.location.pathname.slice(1, indexOfTest + 1);
    var rootPath = rootOrigin + rootDir;
    //var zcJsUrl = rootPath + "dist/ZeroClipboard.Core.js";
    var swfPathBasedOnZeroClipboardJsPath = rootPath + "dist/ZeroClipboard.swf";

    // Test that the client has the expected default URL [even if it's not correct]
    assert.strictEqual(ZeroClipboard.config("swfPath"), swfPathBasedOnZeroClipboardJsPath);
  });


  test("`destroy` destroys the bridge", function(assert) {
    assert.expect(3);

    // Arrange
    ZeroClipboard.isFlashUnusable = function() {
      return false;
    };

    // Assert, arrange, assert, act, assert
    assert.equal(TestUtils.getHtmlBridge(), null, "The bridge does not exist before creating a client");
    ZeroClipboard.create();
    assert.notEqual(TestUtils.getHtmlBridge(), null, "The bridge does exist after creating a client");
    ZeroClipboard.destroy();
    assert.equal(TestUtils.getHtmlBridge(), null, "The bridge does not exist after calling `destroy`");
  });

})(QUnit.module, QUnit.test);
