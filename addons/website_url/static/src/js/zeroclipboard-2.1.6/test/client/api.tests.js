/*global ZeroClipboard, _currentElement:true, _flashState:true, _extend, _clipData, _clipDataFormatMap */

(function(module, test) {
  "use strict";

  var originalFlashState, originalConfig, originalFlashDetect;


  module("client/api.js unit tests - constructor and bridge", {
    setup: function() {
      // Store
      originalFlashDetect = ZeroClipboard.isFlashUnusable;
      originalConfig = ZeroClipboard.config();
      // Modify
      ZeroClipboard.isFlashUnusable = function() {
        return false;
      };
      ZeroClipboard.config({ swfPath: originalConfig.swfPath.replace(/\/(?:src|test)\/.*$/i, "/dist/ZeroClipboard.swf") });
    },
    teardown: function() {
      // Restore
      ZeroClipboard.destroy();
      ZeroClipboard.isFlashUnusable = originalFlashDetect;
      ZeroClipboard.config(originalConfig);
    }
  });


  test("Client is created properly by `ZeroClipboard`", function(assert) {
    assert.expect(3);

    // Arrange & Act
    var client = new ZeroClipboard();

    // Assert
    assert.ok(client);
    assert.ok(client.id);
    assert.strictEqual(client instanceof ZeroClipboard, true);
  });


  test("New client is not the same client (no singleton) but does share the same bridge", function(assert) {
    assert.expect(6);

    // Arrange
    var containerClass = "." + ZeroClipboard.config("containerClass");

    // Assert, arrange, assert, act, assert
    assert.strictEqual($(containerClass).length, 0);
    var client1 = new ZeroClipboard();
    assert.ok(client1.id);
    assert.strictEqual($(containerClass).length, 1);
    var client2 = new ZeroClipboard();
    assert.strictEqual($(containerClass).length, 1);
    assert.notEqual(client2.id, client1.id);
    assert.notEqual(client2, client1);
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


  test("`destroy` clears up the client", function(assert) {
    assert.expect(6);

    // Arrange
    var containerId = "#" + ZeroClipboard.config("containerId");
    ZeroClipboard.isFlashUnusable = function() {
      return false;
    };

    // Assert, arrange, assert, act, assert
    assert.ok(!ZeroClipboard.prototype._singleton, "The client singleton does not exist before creating a client");
    assert.equal($(containerId)[0], null, "The HTML bridge does not exist before creating a client");
    /*jshint nonew:false */
    new ZeroClipboard();
    assert.ok(!ZeroClipboard.prototype._singleton, "The client singleton does exist after creating a client");
    assert.notEqual($(containerId)[0], null, "The HTML bridge does exist after creating a client");
    ZeroClipboard.destroy();
    assert.ok(!ZeroClipboard.prototype._singleton, "The client singleton does not exist after calling `destroy`");
    assert.equal($(containerId)[0], null, "The HTML bridge does not exist after calling `destroy`");
  });


  module("client/api.js unit tests - clipboard", {
    setup: function() {
      // Store
      originalConfig = ZeroClipboard.config();
      // Modify
      ZeroClipboard.config({ swfPath: originalConfig.swfPath.replace(/\/(?:src|test)\/.*$/i, "/dist/ZeroClipboard.swf") });
    },
    teardown: function() {
      ZeroClipboard.destroy();
      ZeroClipboard.config(originalConfig);
    }
  });


  test("`setText` works", function(assert) {
    assert.expect(4);

    // Arrange
    var client = new ZeroClipboard();

    // Assert, Act, repeat ad nauseam
    assert.deepEqual(_clipData, {}, "`_clipData` is empty");

    client.setText("zc4evar");
    assert.deepEqual(_clipData, { "text/plain": "zc4evar" }, "`_clipData` contains expected text");

    client.setText("ZeroClipboard");
    assert.deepEqual(_clipData, { "text/plain": "ZeroClipboard" }, "`_clipData` contains expected updated text");

    _clipData["text/html"] = "<b>Win</b>";
    client.setText("goodbye");
    assert.deepEqual(_clipData, { "text/plain": "goodbye", "text/html": "<b>Win</b>" }, "`_clipData` contains expected updated text AND the other data");
  });


  test("`setHtml` works", function(assert) {
    assert.expect(4);

    // Arrange
    var client = new ZeroClipboard();

    // Assert, Act, repeat ad nauseam
    assert.deepEqual(_clipData, {}, "`_clipData` is empty");

    client.setHtml("zc4evar");
    assert.deepEqual(_clipData, { "text/html": "zc4evar" }, "`_clipData` contains expected HTML");

    client.setHtml("<b>ZeroClipboard</b>");
    assert.deepEqual(_clipData, { "text/html": "<b>ZeroClipboard</b>" }, "`_clipData` contains expected updated HTML");

    _clipData["text/plain"] = "blah";
    client.setHtml("<i>goodbye</i>");
    assert.deepEqual(_clipData, { "text/html": "<i>goodbye</i>", "text/plain": "blah" }, "`_clipData` contains expected updated HTML AND the other data");
  });


  test("`setRichText` works", function(assert) {
    assert.expect(4);

    // Arrange
    var client = new ZeroClipboard();

    // Assert, Act, repeat ad nauseam
    assert.deepEqual(_clipData, {}, "`_clipData` is empty");

    client.setRichText("zc4evar");
    assert.deepEqual(_clipData, { "application/rtf": "zc4evar" }, "`_clipData` contains expected RTF");

    client.setRichText("{\\rtf1\\ansi\n{\\b ZeroClipboard}}");
    assert.deepEqual(_clipData, { "application/rtf": "{\\rtf1\\ansi\n{\\b ZeroClipboard}}" }, "`_clipData` contains expected updated RTF");

    _clipData["text/plain"] = "blah";
    client.setRichText("{\\rtf1\\ansi\n{\\i Foo}}");
    assert.deepEqual(_clipData, { "application/rtf": "{\\rtf1\\ansi\n{\\i Foo}}", "text/plain": "blah" }, "`_clipData` contains expected updated RTF AND the other data");
  });


  test("`setData` works", function(assert) {
    assert.expect(4);

    // Arrange
    var client = new ZeroClipboard();

    // Assert, Act, repeat ad nauseam
    assert.deepEqual(_clipData, {}, "`_clipData` is empty");

    client.setData("text/plain", "zc4evar");
    assert.deepEqual(_clipData, { "text/plain": "zc4evar" }, "`_clipData` contains expected text");

    client.setData("text/html", "<i>ZeroClipboard</i>");
    assert.deepEqual(_clipData, { "text/plain": "zc4evar", "text/html": "<i>ZeroClipboard</i>" }, "`_clipData` contains expected text and custom format");

    client.setData({ "text/html": "<b>Win</b>" });
    assert.deepEqual(_clipData, { "text/html": "<b>Win</b>" }, "`_clipData` contains expected HTML and cleared out old data because an object was passed in");
  });


  test("`clearData` works", function(assert) {
    assert.expect(4);

    // Arrange
    var client = new ZeroClipboard();

    // Assert
    assert.deepEqual(_clipData, {}, "`_clipData` is empty");

    // Arrange & Assert
    _clipData["text/plain"] = "zc4evar";
    _clipData["application/rtf"] = "{\\rtf1\\ansi\n{\\i Foo}}";
    _clipData["text/html"] = "<b>Win</b>";
    assert.deepEqual(_clipData, {
      "text/plain": "zc4evar",
      "application/rtf": "{\\rtf1\\ansi\n{\\i Foo}}",
      "text/html": "<b>Win</b>"
    }, "`_clipData` contains all expected data");

    // Act & Assert
    client.clearData("application/rtf");
    assert.deepEqual(_clipData, {
      "text/plain": "zc4evar",
      "text/html": "<b>Win</b>"
    }, "`_clipData` had 'application/rtf' successfully removed");

    // Act & Assert
    client.clearData();
    assert.deepEqual(_clipData, {}, "`_clipData` had all data successfully removed");
  });


  test("`setText` overrides the data-clipboard-text attribute", function(assert) {
    assert.expect(3);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button");

    // Act
    client.clip(currentEl);
    client.setText("This is the new text");
    ZeroClipboard.activate(currentEl);
    var pendingText = ZeroClipboard.emit("copy");

    // Assert
    assert.deepEqual(_clipData, { "text/plain": "This is the new text" });
    assert.deepEqual(pendingText, { "text": "This is the new text" });
    assert.deepEqual(_clipDataFormatMap, { "text": "text/plain" });
  });


  test("`setText` overrides data-clipboard-target pre", function(assert) {
    assert.expect(3);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button_pre_text");

    // Act
    client.clip(currentEl);
    client.setText("This is the new text");
    ZeroClipboard.activate(currentEl);
    var pendingText = ZeroClipboard.emit("copy");

    // Assert
    assert.deepEqual(_clipData, { "text/plain": "This is the new text" });
    assert.deepEqual(pendingText, { "text": "This is the new text" });
    assert.deepEqual(_clipDataFormatMap, { "text": "text/plain" });
  });


  test("`setHtml` overrides data-clipboard-target pre", function(assert) {
    assert.expect(3);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button_pre_text");

    // Act
    client.clip(currentEl);
    client.setHtml("This is the new HTML");
    ZeroClipboard.activate(currentEl);
    var pendingText = ZeroClipboard.emit("copy");

    // Assert
    assert.deepEqual(_clipData, { "text/html": "This is the new HTML" });
    assert.deepEqual(pendingText, { "html": "This is the new HTML" });
    assert.deepEqual(_clipDataFormatMap, { "html": "text/html" });
  });


  test("`setText` AND `setHtml` override data-clipboard-target pre", function(assert) {
    assert.expect(3);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button_pre_text");

    // Act
    client.clip(currentEl);
    client.setText("This is the new text");
    client.setHtml("This is the new HTML");
    ZeroClipboard.activate(currentEl);
    var pendingText = ZeroClipboard.emit("copy");

    // Assert
    assert.deepEqual(_clipData, {
      "text/plain": "This is the new text",
      "text/html": "This is the new HTML"
    });
    assert.deepEqual(pendingText, {
      "text": "This is the new text",
      "html": "This is the new HTML"
    });
    assert.deepEqual(_clipDataFormatMap, { "text": "text/plain", "html": "text/html" });
  });


  module("client/api.js unit tests - event", {
    setup: function() {
      // Store
      originalFlashState = _extend({}, _flashState);
      originalConfig = ZeroClipboard.config();
      originalFlashDetect = ZeroClipboard.isFlashUnusable;
      // Modify
      _currentElement = null;
      _flashState = {
        bridge: null,
        version: "0.0.0",
        disabled: null,
        outdated: null,
        unavailable: null,
        deactivated: null,
        ready: null
      };
      //ZeroClipboard.config({ swfPath: originalConfig.swfPath.replace(/\/(?:src|test)\/.*$/i, "/dist/ZeroClipboard.swf") });
    },
    teardown: function() {
      ZeroClipboard.destroy();
      _currentElement = null;
      _flashState = originalFlashState;
      ZeroClipboard.config(originalConfig);
      ZeroClipboard.isFlashUnusable = originalFlashDetect;
    }
  });


  test("Clip element after new client", function(assert) {
    assert.expect(4);

    // Arrange
    var client = new ZeroClipboard();
    var target = document.getElementById("d_clip_button");

    // Assert, Act, Assert
    assert.strictEqual("zcClippingId" in target, false);
    assert.deepEqual(client.elements(), []);
    client.clip(target);
    assert.strictEqual("zcClippingId" in target, true);
    assert.deepEqual(client.elements(), [target]);
  });


  test("unclip element removes items", function(assert) {
    assert.expect(12);

    // Arrange
    var client = new ZeroClipboard();
    var targets = [
      document.getElementById("d_clip_button"),
      document.getElementById("d_clip_button2"),
      document.getElementById("d_clip_button3")
    ];

    // Assert pre-conditions
    assert.strictEqual("zcClippingId" in targets[0], false);
    assert.strictEqual("zcClippingId" in targets[1], false);
    assert.strictEqual("zcClippingId" in targets[2], false);
    assert.deepEqual(client.elements(), []);

    // Act
    client.clip(targets);

    // Assert initial state
    assert.strictEqual("zcClippingId" in targets[0], true);
    assert.strictEqual("zcClippingId" in targets[1], true);
    assert.strictEqual("zcClippingId" in targets[2], true);
    assert.deepEqual(client.elements(), targets);

    // Act more
    client.unclip([
      document.getElementById("d_clip_button3"),
      document.getElementById("d_clip_button2")
    ]);

    // Assert end state
    assert.strictEqual("zcClippingId" in targets[0], true);
    assert.strictEqual("zcClippingId" in targets[1], false);
    assert.strictEqual("zcClippingId" in targets[2], false);
    assert.deepEqual(client.elements(), [targets[0]]);
  });


  test("Element won't be clipped twice", function(assert) {
    assert.expect(3);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button");

    // Assert, act, assert
    assert.deepEqual(client.elements(), []);
    client.clip(currentEl);
    assert.deepEqual(client.elements(), [currentEl]);
    client.clip(currentEl);
    assert.deepEqual(client.elements(), [currentEl]);
  });


  test("Registering Events", function(assert) {
    assert.expect(6);

    // Arrange
    var client = new ZeroClipboard();

    // Act
    client.on("ready", function(){});
    client.on("onError", function(){});
    client.on("onCustomEvent", function(){});

    // Assert
    assert.ok(client.handlers().ready);
    assert.ok(client.handlers().error);
    assert.ok(client.handlers().customevent);
    assert.strictEqual(client.handlers().ready.length, 1);
    assert.strictEqual(client.handlers().error.length, 1);
    assert.strictEqual(client.handlers().customevent.length, 1);
  });


  test("Registering Events with Maps", function(assert) {
    assert.expect(6);

    // Arrange
    var client = new ZeroClipboard();

    // Act
    client.on({
      "ready": function(){},
      "onError": function(){},
      "onCustomEvent": function(){}
    });

    // Assert
    assert.ok(client.handlers().ready);
    assert.ok(client.handlers().error);
    assert.ok(client.handlers().customevent);
    assert.strictEqual(client.handlers().ready.length, 1);
    assert.strictEqual(client.handlers().error.length, 1);
    assert.strictEqual(client.handlers().customevent.length, 1);
  });


  test("Unregistering Events", function(assert) {
    assert.expect(6);

    // Arrange
    var client = new ZeroClipboard();
    var ready = function(){};
    var onError = function(){};
    var onCustomEvent = function(){};

    // Act
    client.on("ready", ready);
    client.on("onError", onError);
    client.on("onCustomEvent", onCustomEvent);

    // Assert
    assert.deepEqual(client.handlers().ready, [ready]);
    assert.deepEqual(client.handlers().error, [onError]);
    assert.deepEqual(client.handlers().customevent, [onCustomEvent]);

    // Act & Assert
    client.off("ready", ready);
    assert.deepEqual(client.handlers().ready, []);

    // Act & Assert
    client.off("onError", onError);
    assert.deepEqual(client.handlers().error, []);

    // Act & Assert
    client.off("onCustomEvent", onCustomEvent);
    assert.deepEqual(client.handlers().customevent, []);
  });


  test("Unregistering Events with Maps", function(assert) {
    assert.expect(6);

    // Arrange
    var client = new ZeroClipboard();
    var ready = function(){};
    var onError = function(){};
    var onCustomEvent = function(){};

    // Act
    client.on("ready", ready);
    client.on("onError", onError);
    client.on("onCustomEvent", onCustomEvent);

    // Assert
    assert.deepEqual(client.handlers().ready, [ready]);
    assert.deepEqual(client.handlers().error, [onError]);
    assert.deepEqual(client.handlers().customevent, [onCustomEvent]);

    // Act & Assert
    client.off({ "ready": ready });
    assert.deepEqual(client.handlers().ready, []);

    // Act & Assert
    client.off({ "onError": onError });
    assert.deepEqual(client.handlers().error, []);

    // Act & Assert
    client.off({ "onCustomEvent": onCustomEvent });
    assert.deepEqual(client.handlers().customevent, []);
  });


  test("Registering two events works", function(assert) {
    assert.expect(6);

    // Arrange
    var client = new ZeroClipboard();

    // Assert
    assert.ok(!client.handlers().ready);
    assert.ok(!client.handlers().aftercopy);

    // Act
    client.on("ready onaftercopy", function(){});

    // Assert more
    assert.ok(client.handlers().ready);
    assert.ok(client.handlers().aftercopy);
    assert.strictEqual(client.handlers().ready.length, 1);
    assert.strictEqual(client.handlers().aftercopy.length, 1);
  });


  test("Registering two events with a map works", function(assert) {
    assert.expect(6);

    // Arrange
    var client = new ZeroClipboard();

    // Assert
    assert.ok(!client.handlers().ready);
    assert.ok(!client.handlers().aftercopy);

    // Act
    client.on({
      "ready onaftercopy": function(){}
    });

    // Assert more
    assert.ok(client.handlers().ready);
    assert.ok(client.handlers().aftercopy);
    assert.strictEqual(client.handlers().ready.length, 1);
    assert.strictEqual(client.handlers().aftercopy.length, 1);
  });


  test("Unregistering two events works", function(assert) {
    assert.expect(6);

    // Arrange
    var client = new ZeroClipboard();
    var func = function() {};

    // Assert
    assert.ok(!client.handlers().ready);
    assert.ok(!client.handlers().aftercopy);

    // Act
    client.on("ready onaftercopy", func);

    // Assert more
    assert.deepEqual(client.handlers().ready, [func]);
    assert.deepEqual(client.handlers().aftercopy, [func]);

    // Act more
    client.off("ready onaftercopy", func);

    // Assert even more
    assert.deepEqual(client.handlers().ready, []);
    assert.deepEqual(client.handlers().aftercopy, []);
  });


  test("Unregistering two events with a map works", function(assert) {
    assert.expect(6);

    // Arrange
    var client = new ZeroClipboard();
    var func = function() {};

    // Assert
    assert.ok(!client.handlers().ready);
    assert.ok(!client.handlers().aftercopy);

    // Act
    client.on("ready onaftercopy", func);

    // Assert more
    assert.deepEqual(client.handlers().ready, [func]);
    assert.deepEqual(client.handlers().aftercopy, [func]);

    // Act more
    client.off({
      "ready onaftercopy": func
    });

    // Assert even more
    assert.deepEqual(client.handlers().ready, []);
    assert.deepEqual(client.handlers().aftercopy, []);
  });


  test("`on` can add multiple handlers for the same event", function(assert) {
    assert.expect(3);

    // Arrange
    var client = new ZeroClipboard();
    var func1 = function() {};
    var func2 = function() {};

    // Assert
    assert.ok(!client.handlers().ready);

    // Act
    client.on("ready", func1);

    // Assert more
    assert.deepEqual(client.handlers().ready, [func1]);

    // Act more
    client.on("ready", func2);

    // Assert even more
    assert.deepEqual(client.handlers().ready, [func1, func2]);
  });


  test("`off` can remove multiple handlers for the same event", function(assert) {
    assert.expect(5);

    // Arrange
    var client = new ZeroClipboard();
    var func1 = function() {};
    var func2 = function() {};
    var func3 = function() {};

    // Assert
    assert.ok(!client.handlers().ready);

    // Act
    client.on("ready", func1);
    client.on("ready", func2);
    client.on("ready", func3);

    // Assert more
    assert.deepEqual(client.handlers().ready, [func1, func2, func3]);

    // Act and assert even more
    client.off("ready", func3);  // Remove from the end
    assert.deepEqual(client.handlers().ready, [func1, func2]);

    client.off("ready", func1);  // Remove from the start
    assert.deepEqual(client.handlers().ready, [func2]);

    client.off("ready", func2);  // Remove the last one
    assert.deepEqual(client.handlers().ready, []);
  });


  test("`on` can add more than one entry of the same handler function for the same event", function(assert) {
    assert.expect(2);

    // Arrange
    var client = new ZeroClipboard();
    var func1 = function() {};

    // Assert
    assert.ok(!client.handlers().ready);

    // Act
    client.on("ready", func1);
    client.on("ready", func1);

    // Assert more
    assert.deepEqual(client.handlers().ready, [func1, func1]);
  });


  test("`off` will remove all entries of the same handler function for the same event", function(assert) {
    assert.expect(3);

    // Arrange
    var client = new ZeroClipboard();
    var func1 = function() {};

    // Assert
    assert.ok(!client.handlers().ready);

    // Act
    client.on("ready", func1);
    client.on("ready", func1);

    // Assert more
    assert.deepEqual(client.handlers().ready, [func1, func1]);

    // Act more
    client.off("ready", func1);

    // Assert even more
    assert.deepEqual(client.handlers().ready, []);
  });


  test("`off` will remove all handler functions for an event if no function is specified", function(assert) {
    assert.expect(3);

    // Arrange
    var client = new ZeroClipboard();
    var func1 = function() {};
    var func2 = function() {};
    var func3 = function() {};

    // Assert
    assert.ok(!client.handlers().ready);

    // Act
    client.on("ready", func1);
    client.on("ready", func2);
    client.on("ready", func3);
    client.on("ready", func1);

    // Assert more
    assert.deepEqual(client.handlers().ready, [func1, func2, func3, func1]);

    // Act and assert even more
    client.off("ready");  // Remove all
    assert.deepEqual(client.handlers().ready, []);
  });


  test("`off` will remove all handler functions for all events if no event type is specified", function(assert) {
    assert.expect(6);

    // Arrange
    var client = new ZeroClipboard();
    var func1 = function() {};
    var func2 = function() {};
    var func3 = function() {};

    // Assert
    assert.ok(!client.handlers().ready);
    assert.ok(!client.handlers().error);

    // Act
    client.on("ready", func1);
    client.on("ready", func2);
    client.on("error", func3);

    // Assert more
    assert.deepEqual(client.handlers().ready, [func1, func2]);
    assert.deepEqual(client.handlers().error, [func3]);

    // Act and assert even more
    client.off();  // Remove all handlers for all types
    assert.deepEqual(client.handlers().ready, []);
    assert.deepEqual(client.handlers().error, []);
  });


  test("Test disabledFlash Event", function(assert) {
    assert.expect(6);

    // Arrange
    _flashState.disabled = true;
    var client = new ZeroClipboard();
    var id = client.id;

    // Act (should auto-fire immediately but the handler will be invoked asynchronously)
    client.on( "error", function(event) {
      // Assert
      assert.strictEqual(this, client);
      assert.strictEqual(this.id, id);
      assert.strictEqual(_flashState.disabled, true);
      assert.strictEqual(event.type, "error");
      assert.strictEqual(event.name, "flash-disabled");
      assert.strictEqual(event.target, null);
      QUnit.start();
    } );
    QUnit.stop();
  });


  test("Test outdatedFlash Event", function(assert) {
    assert.expect(8);

    // Arrange
    _flashState.disabled = false;
    _flashState.outdated = true;
    _flashState.version = "10.0.0";
    var client = new ZeroClipboard();
    var id = client.id;

    // Act
    client.on( "ready", function(/* event */) {
      assert.ok(false, "The `ready` event should NOT have fired!");
    } );
    client.on( "error", function(event) {
      // Assert
      assert.strictEqual(this, client);
      assert.strictEqual(this.id, id);
      assert.strictEqual(_flashState.outdated, true);
      assert.strictEqual(event.type, "error");
      assert.strictEqual(event.name, "flash-outdated");
      assert.strictEqual(event.target, null);
      assert.strictEqual(event.version, "10.0.0");
      assert.strictEqual(event.minimumVersion, "11.0.0");
      QUnit.start();
    } );
    QUnit.stop();
  });


  test("Test deactivatedFlash Event", function(assert) {
    assert.expect(10);

    // Arrange
    _flashState.disabled = false;
    _flashState.outdated = false;
    _flashState.version = "11.0.0";
    ZeroClipboard.config({ flashLoadTimeout: 2000 });
    var client = new ZeroClipboard();
    var id = client.id;
    client.on( "ready", function(/* event */) {
      assert.ok(false, "The `ready` event should NOT have fired!");
    } );
    client.on( "error", function(event) {
      // Assert
      assert.strictEqual(this, client);
      assert.strictEqual(this.id, id);
      assert.strictEqual(_flashState.deactivated, true);
      assert.strictEqual(_flashState.ready, false);
      assert.strictEqual(event.type, "error");
      assert.strictEqual(event.name, "flash-deactivated");
      assert.strictEqual(event.target, null);
      assert.strictEqual(event.version, "11.0.0");
      assert.strictEqual(event.minimumVersion, "11.0.0");
      QUnit.start();
    } );

    // Act
    setTimeout(function() {
      assert.strictEqual(_flashState.deactivated, null);
    }, 500);
    QUnit.stop();
    // The "deactivatedFlash" event will automatically fire in 2 seconds if the `ready` event does not fire first
  });


  test("Test deactivatedFlash Event after first resolution", function(assert) {
    assert.expect(8);

    // Arrange
    _flashState.disabled = false;
    _flashState.outdated = false;
    _flashState.version = "11.0.0";
    _flashState.deactivated = true;
    var client = new ZeroClipboard();
    var id = client.id;
    client.on( "ready", function(/* event */) {
      assert.ok(false, "The `ready` event should NOT have fired!");
    } );
    client.on( "error", function(event) {
      // Assert
      assert.strictEqual(this, client);
      assert.strictEqual(this.id, id);
      assert.strictEqual(_flashState.deactivated, true);
      assert.strictEqual(event.type, "error");
      assert.strictEqual(event.name, "flash-deactivated");
      assert.strictEqual(event.target, null);
      assert.strictEqual(event.version, "11.0.0");
      assert.strictEqual(event.minimumVersion, "11.0.0");
      QUnit.start();
    } );

    // Act
    QUnit.stop();
    // The "deactivatedFlash" event will automatically fire in 0 seconds (when the event loop gets to it)
  });


  test("Test ready Event", function(assert) {
    assert.expect(6);

    // Arrange
    _flashState.disabled = false;
    _flashState.outdated = false;
    _flashState.version = "11.9.0";
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button");
    var id = client.id;
    client.clip(currentEl);
    client.on( "ready", function(event) {
      // Assert
      assert.strictEqual(this, client);
      assert.strictEqual(this.id, id);
      assert.strictEqual(event.type, "ready");
      assert.strictEqual(event.target, null);
      assert.strictEqual(_flashState.deactivated, false);
      assert.strictEqual(event.version, "11.9.0");
      QUnit.start();
    } );

    // Act
    QUnit.stop();
    ZeroClipboard.emit("ready");
  });


  test("Test ready Event after first load", function(assert) {
    assert.expect(6);

    // Arrange
    _flashState.disabled = false;
    _flashState.outdated = false;
    _flashState.deactivated = false;
    _flashState.version = "11.9.0";
    _flashState.ready = true;
    _flashState.bridge = {};
    var client = new ZeroClipboard();
    var id = client.id;

    // Act (should auto-fire immediately but the handler will be invoked asynchronously)
    client.on( "ready", function(event) {
      // Assert
      assert.strictEqual(this, client);
      assert.strictEqual(this.id, id);
      assert.strictEqual(event.type, "ready");
      assert.strictEqual(event.target, null);
      assert.strictEqual(_flashState.deactivated, false);
      assert.strictEqual(event.version, "11.9.0");
      QUnit.start();
    } );
    QUnit.stop();
  });


  test("Test overdueFlash Event", function(assert) {
    assert.expect(15);

    // Arrange
    _flashState.disabled = false;
    _flashState.outdated = false;
    _flashState.version = "11.0.0";
    _flashState.deactivated = true;
    var client = new ZeroClipboard();
    var id = client.id;
    client.on( "ready", function(/* event */) {
      assert.ok(false, "The `ready` event should NOT have fired!");
    } );
    client.on( "error", function(event) {
      // Assert
      assert.strictEqual(this, client);
      assert.strictEqual(this.id, id);
      if (event.name === "flash-deactivated") {
        assert.strictEqual(event.type, "error");
        assert.strictEqual(event.name, "flash-deactivated");
        assert.strictEqual(_flashState.deactivated, true);
        assert.strictEqual(event.version, "11.0.0");
        assert.strictEqual(event.minimumVersion, "11.0.0");
      }
      else if (event.name === "flash-overdue") {
        assert.strictEqual(event.type, "error");
        assert.strictEqual(event.name, "flash-overdue");
        assert.strictEqual(_flashState.deactivated, false);
        assert.strictEqual(_flashState.overdue, true);
        assert.strictEqual(event.version, "11.0.0");
        assert.strictEqual(event.minimumVersion, "11.0.0");

        QUnit.start();
      }
    } );

    // Act
    QUnit.stop();
    // The "deactivatedFlash" event will automatically fire in 0 seconds (when the event loop gets to it)

    setTimeout(function() {
      // Emit a "ready" event (as if from the SWF) to trigger an "overdueFlash" event
      ZeroClipboard.emit("ready");
    }, 1000);
  });


  test("Test string function name as handler", function(assert) {
    assert.expect(2);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button");
    var id = client.id;
    client.clip(currentEl);
    window.zcLoadCallback = function(event) {
      // Assert
      assert.strictEqual(this.id, id);
      assert.strictEqual(event.type, "ready");
      QUnit.start();
      delete window.zcLoadCallback;
    };
    client.on( "ready", "zcLoadCallback" );

    // Act
    QUnit.stop();
    ZeroClipboard.emit("ready");
  });


  test("Test EventListener object as handler", function(assert) {
    assert.expect(4);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button");
    var id = client.id;
    client.clip(currentEl);
    var eventListenerObj = {
      handleEvent: function(event) {
        // Assert
        assert.strictEqual(event.type, "ready");
        assert.strictEqual(event.client, client);
        assert.strictEqual(event.client.id, id);
        assert.strictEqual(this, eventListenerObj);
        QUnit.start();
      }
    };
    client.on( "ready", eventListenerObj );

    // Act
    QUnit.stop();
    ZeroClipboard.emit("ready");
  });


  test("Test for appropriate context inside of invoked event handlers", function(assert) {
    assert.expect(12);

    // Arrange
    var client = new ZeroClipboard();
    var currentEl = document.getElementById("d_clip_button");
    assert.ok(currentEl);
    assert.strictEqual(currentEl.id, "d_clip_button");

    client.clip(currentEl);
    ZeroClipboard.activate(currentEl);

    client.on( "ready error", function(/* event */) {
      // Assert
      assert.strictEqual(this, client);
    } );
    client.on( "beforecopy", function(event) {
      // Assert
      assert.strictEqual(event.target, currentEl);
    } );
    client.on( "copy", function(event) {
      // Assert
      assert.strictEqual(event.target, currentEl);
      assert.ok(_clipData["text/plain"]);
    } );
    client.on( "aftercopy", function(event) {
      // Assert
      assert.strictEqual(event.target, currentEl);
      assert.ok(!_clipData["text/plain"]);
      QUnit.start();
    } );

    // Act
    QUnit.stop();
    ZeroClipboard.emit("ready");
    ZeroClipboard.emit({"type":"error", "name":"flash-disabled"});
    ZeroClipboard.emit({"type":"error", "name":"flash-outdated"});
    ZeroClipboard.emit({"type":"error", "name":"flash-deactivated"});
    ZeroClipboard.emit({"type":"error", "name":"flash-overdue"});
    ZeroClipboard.emit("beforecopy");
    ZeroClipboard.emit("copy");
    ZeroClipboard.emit("aftercopy");
  });


  module("client/api.js unit tests - element clipping", {
    setup: function() {
      // Store
      originalConfig = ZeroClipboard.config();
      // Modify
      ZeroClipboard.config({ swfPath: originalConfig.swfPath.replace(/\/(?:src|test)\/.*$/i, "/dist/ZeroClipboard.swf") });
    },
    teardown: function() {
      ZeroClipboard.destroy();
      ZeroClipboard.config(originalConfig);
    }
  });


  test("Client without selector doesn't have elements", function(assert) {
    assert.expect(2);

    // Arrange & Act
    var client = new ZeroClipboard();

    // Assert
    assert.ok(client);
    assert.deepEqual(client.elements(), []);
  });


})(QUnit.module, QUnit.test);
