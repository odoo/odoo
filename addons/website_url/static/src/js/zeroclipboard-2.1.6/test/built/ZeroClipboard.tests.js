/*global ZeroClipboard */

(function(module, test) {
  "use strict";

  var originalConfig, originalFlashDetect;

  // Helper functions
  var TestUtils = {
    getHtmlBridge: function() {
      return document.getElementById(ZeroClipboard.config("containerId"));
    }
  };


  module("ZeroClipboard.js (built) unit tests - Core", {
    setup: function() {
      // Store
      originalConfig = ZeroClipboard.config();
      originalFlashDetect = ZeroClipboard.isFlashUnusable;
      // Modify
      ZeroClipboard.isFlashUnusable = function() {
        return false;
      };
      ZeroClipboard.config({ swfPath: originalConfig.swfPath.replace(/\/(?:src|test)\/.*$/i, "/dist/ZeroClipboard.swf") });
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
    //var zcJsUrl = rootPath + "dist/ZeroClipboard.js";
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
    /*jshint nonew:false */
    new ZeroClipboard();
    assert.notEqual(TestUtils.getHtmlBridge(), null, "The bridge does exist after creating a client");
    ZeroClipboard.destroy();
    assert.equal(TestUtils.getHtmlBridge(), null, "The bridge does not exist after calling `destroy`");
  });




  module("ZeroClipboard.js (built) unit tests - Client", {
    setup: function() {
      // Store
      originalConfig = ZeroClipboard.config();
      originalFlashDetect = ZeroClipboard.isFlashUnusable;
      // Modify
      ZeroClipboard.isFlashUnusable = function() {
        return false;
      };
      ZeroClipboard.config({ swfPath: originalConfig.swfPath.replace(/\/(?:src|test)\/.*$/i, "/dist/ZeroClipboard.swf") });
    },
    teardown: function() {
      // Restore
      ZeroClipboard.destroy();
      ZeroClipboard.config(originalConfig);
      ZeroClipboard.isFlashUnusable = originalFlashDetect;
    }
  });

  test("`ZeroClipboard` exists", function(assert) {
    assert.expect(1);

    // Arrange -> N/A

    // Act -> N/A

    // Assert
    assert.ok(ZeroClipboard);
  });

  test("Client is created properly", function(assert) {
    assert.expect(2);

    // Arrange & Act
    var client = new ZeroClipboard();

    // Assert
    assert.ok(client);
    assert.ok(client.id);
  });

  test("Client without selector doesn't have elements", function(assert) {
    assert.expect(2);

    // Arrange & Act
    var client = new ZeroClipboard();

    // Assert
    assert.ok(client);
    assert.deepEqual(client.elements(), []);
  });

  test("Object has a title", function(assert) {
    assert.expect(1);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button");

    // Act
    client.clip(currentEl);
    ZeroClipboard.activate(currentEl);

    // Assert
    assert.strictEqual(TestUtils.getHtmlBridge().getAttribute("title"), "Click me to copy to clipboard.");

    // Revert
    ZeroClipboard.deactivate();
  });

  test("Object has no title", function(assert) {
    assert.expect(1);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button_no_title");

    // Act
    client.clip(currentEl);
    ZeroClipboard.activate(currentEl);

    // Assert
    assert.ok(!TestUtils.getHtmlBridge().getAttribute("title"));
  });

  test("Object doesn't have data-clipboard-text", function(assert) {
    assert.expect(1);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button_no_text");

    // Act
    client.clip(currentEl);
    ZeroClipboard.activate(currentEl);

    // Assert
    assert.ok(!TestUtils.getHtmlBridge().getAttribute("data-clipboard-text"));
  });

  test("New client is not the same client (no singleton) but does share the same bridge", function(assert) {
    assert.expect(6);

    // Assert, arrange, assert, act, assert
    var containerClass = "." + ZeroClipboard.config("containerClass");
    assert.strictEqual($(containerClass).length, 0);
    var client1 = new ZeroClipboard();
    assert.ok(client1.id);
    assert.strictEqual($(containerClass).length, 1);
    var client2 = new ZeroClipboard();
    assert.strictEqual($(containerClass).length, 1);
    assert.notEqual(client2.id, client1.id);
    assert.notEqual(client2, client1);
  });

  test("Calculations based on borderWidth never return NaN", function(assert) {
    assert.expect(4);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button");

    // Act
    client.clip(currentEl);
    ZeroClipboard.activate(currentEl);

    // Assert
    var htmlBridge = TestUtils.getHtmlBridge();
    assert.strictEqual(/^-?[0-9\.]+px$/.test(htmlBridge.style.top), true);
    assert.strictEqual(/^-?[0-9\.]+px$/.test(htmlBridge.style.left), true);
    assert.strictEqual(/^-?[0-9\.]+px$/.test(htmlBridge.style.width), true);
    assert.strictEqual(/^-?[0-9\.]+px$/.test(htmlBridge.style.height), true);
  });

  test("No more client singleton!", function(assert) {
    assert.expect(7);

    // Arrange
    ZeroClipboard.isFlashUnusable = function() {
      return false;
    };

    // Assert, arrange, assert, act, assert
    assert.ok(!ZeroClipboard.prototype._singleton, "The client singleton does not exist on the prototype before creating a client");
    var client1 = new ZeroClipboard();
    assert.ok(!ZeroClipboard.prototype._singleton, "The client singleton does not exist on the prototype after creating a client");
    assert.ok(!client1._singleton, "The client singleton does not exist on the client instance after creating a client");
    var client2 = new ZeroClipboard();
    assert.ok(!ZeroClipboard.prototype._singleton, "The client singleton does not exist on the prototype after creating a second client");
    assert.ok(!client1._singleton, "The client singleton does not exist on the first client instance after creating a second client");
    assert.ok(!client2._singleton, "The client singleton does not exist on the second client instance after creating a second client");
    ZeroClipboard.destroy();
    assert.ok(!ZeroClipboard.prototype._singleton, "The client singleton does not exist on the prototype after calling `destroy`");
  });


})(QUnit.module, QUnit.test);
