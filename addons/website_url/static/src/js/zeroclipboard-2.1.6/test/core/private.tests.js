/*global _flashState:true, _currentElement:true, _copyTarget:true, _extend, _getStyle, _removeClass, _addClass, _vars, _cacheBust, _extractDomain, _determineScriptAccess, _mapClipDataToFlash, _mapClipResultsFromFlash, _createEvent, _preprocessEvent, _getRelatedTarget, _shouldPerformAsync, _dispatchCallback, _detectFlashSupport */

(function(module, test) {
  "use strict";

  var mimeType, ax, flashState;


  module("core/private.js unit tests - utils");


  test("`_getStyle` returns computed styles", function(assert) {
    assert.expect(5);

    // Arrange
    var pointerEl    = $("a.no_cursor_style")[0];
    var nonPointerEl = $("a.no_pointer_anchor")[0];
    var zIndexAutoEl = $(".zindex-auto")[0];
    var clipButtonEl = $("#d_clip_button")[0];
    var bigBorderEl  = $(".big-border")[0];

    // Act
    var pointerElComputedCursor = _getStyle(pointerEl, "cursor");
    var nonPointerElComputedCursor = _getStyle(nonPointerEl, "cursor");
    var zIndexAutoElComputedZIndex = _getStyle(zIndexAutoEl, "z-index");
    var clipButtonElComputedBorderLeftWidth = _getStyle(clipButtonEl, "border-left-width");
    var bigBorderElComputedBorderLeftWith = _getStyle(bigBorderEl, "border-left-width");

    // Assert
    assert.strictEqual(pointerElComputedCursor, "pointer");
    assert.notStrictEqual(nonPointerElComputedCursor, "pointer");
    // Returns 0 in IE7, "auto" everywhere else
    assert.strictEqual(/^(?:auto|0)$/.test(zIndexAutoElComputedZIndex), true);
    // This varies between "0px" and "3px" depending on the browser (WAT?)
    assert.strictEqual(/^[0-3]px$/.test(clipButtonElComputedBorderLeftWidth), true);
    assert.strictEqual(bigBorderElComputedBorderLeftWith, "10px");
  });


  test("`_removeClass` removes classes from element", function(assert) {
    assert.expect(5);

    // Arrange
    var div = $("<div></div>").addClass("class1 class-2 class_3")[0];

    // Act & Assert
    _removeClass(div, "class1");
    assert.strictEqual(div.className, "class-2 class_3");

    _removeClass(div, "classd");
    assert.strictEqual(div.className, "class-2 class_3");

    _removeClass(div, "class-2");
    assert.strictEqual(div.className, "class_3");

    _removeClass(div, "class_3");
    assert.strictEqual(div.className, "");

    _removeClass(div, "class-3");
    assert.strictEqual(div.className, "");

    div = null;
  });


  test("`_removeClass` doesn't remove partial class names", function(assert) {
    assert.expect(3);

    // Arrange
    var div = $("<div></div>").addClass("class1 class-2 class_3")[0];

    // Act & Assert
    _removeClass(div, "ass");
    assert.strictEqual(div.className, "class1 class-2 class_3");

    _removeClass(div, "-2");
    assert.strictEqual(div.className, "class1 class-2 class_3");

    _removeClass(div, "_3");
    assert.strictEqual(div.className, "class1 class-2 class_3");

    div = null;
  });


  test("`_addClass` adds a class name", function(assert) {
    assert.expect(4);

    // Arrange
    var div = $("<div></div>")[0];

    // Act & Assert
    _addClass(div, "class1");
    assert.strictEqual(div.className, "class1");

    _addClass(div, "class-2");
    assert.strictEqual(div.className, "class1 class-2");

    _addClass(div, "class_3");
    assert.strictEqual(div.className, "class1 class-2 class_3");

    _addClass(div, "class_3");
    assert.strictEqual(div.className, "class1 class-2 class_3");

    div = null;
  });


  test("`_vars` builds FlashVars", function(assert) {
    assert.expect(6);

    // Arrange
    var clipOptionsEmpty = {};
    var clipOptionsTrustedDomains = {
      trustedDomains: ["*"]
    };
    var clipOptionsEnhancedClipboardFalse = {
      forceEnhancedClipboard: false
    };
    var clipOptionsEnhancedClipboardTrue = {
      forceEnhancedClipboard: true
    };
    var clipOptionsTrustedDomainsPlusEnhancedClipboardFalse = {
      trustedDomains: ["*"],
      forceEnhancedClipboard: false
    };
    var clipOptionsTrustedDomainsPlusEnhancedClipboardTrue = {
      trustedDomains: ["*"],
      forceEnhancedClipboard: true
    };

    // Act & Assert
    assert.strictEqual(_vars(clipOptionsEmpty), "");
    assert.strictEqual(_vars(clipOptionsTrustedDomains), "trustedOrigins=*");
    assert.strictEqual(_vars(clipOptionsEnhancedClipboardFalse), "");
    assert.strictEqual(_vars(clipOptionsEnhancedClipboardTrue), "forceEnhancedClipboard=true");
    assert.strictEqual(_vars(clipOptionsTrustedDomainsPlusEnhancedClipboardFalse), "trustedOrigins=*");
    assert.strictEqual(_vars(clipOptionsTrustedDomainsPlusEnhancedClipboardTrue), "trustedOrigins=*&forceEnhancedClipboard=true");
  });


  test("`_cacheBust` adds cache-buster appropriately", function(assert) {
    assert.expect(2);

    // Arrange
    var pathWithoutQuery = "path.com/z.swf";
    var pathWithQuery = "path.com/z.swf?q=jon";

    // Act & Assert
    assert.strictEqual(_cacheBust(pathWithoutQuery).indexOf("?noCache="), 0);
    assert.strictEqual(_cacheBust(pathWithQuery).indexOf("&noCache="), 0);
  });


  test("`_cacheBust` can be disabled", function(assert) {
    assert.expect(2);

    // Arrange
    var pathWithoutQuery = "path.com/z.swf";
    var pathWithQuery = "path.com/z.swf?q=jon";
    var options = {
      cacheBust: false
    };

    // Act & Assert
    assert.strictEqual(_cacheBust(pathWithoutQuery, options), "");
    assert.strictEqual(_cacheBust(pathWithQuery, options), "");
  });


  test("`_extractDomain` extracts domains from origins and URLs", function(assert) {
    assert.expect(20);

    // Arrange
    var inputToExpectedMap = {
      "": null,
      " ": null,
      "ZeroClipboard.swf": null,
      "js/ZeroClipboard.swf": null,
      "/js/ZeroClipboard.swf": null,
      "/zeroclipboard/zeroclipboard/": null,
      "zeroclipboard/zeroclipboard/": null,
      "*": "*",
      "github.com": "github.com",
      "http://github.com": "github.com",
      "https://github.com": "github.com",
      "github.com:80": "github.com:80",
      "http://github.com:80": "github.com:80",
      "https://github.com:443": "github.com:443",
      "http://github.com/zeroclipboard/zeroclipboard/": "github.com",
      "https://github.com/zeroclipboard/zeroclipboard/": "github.com",
      "http://github.com:80/zeroclipboard/zeroclipboard/": "github.com:80",
      "https://github.com:443/zeroclipboard/zeroclipboard/": "github.com:443"
    };

    // Act & Assert
    assert.strictEqual(_extractDomain(undefined), null, "Processing: `undefined`");
    assert.strictEqual(_extractDomain(null), null, "Processing: `null`");
    for (var originOrUrl in inputToExpectedMap) {
      if (inputToExpectedMap.hasOwnProperty(originOrUrl)) {
        assert.strictEqual(_extractDomain(originOrUrl), inputToExpectedMap[originOrUrl], "Processing: \"" + originOrUrl + "\"");
      }
    }
  });


  test("`_determineScriptAccess` determines the appropriate script access level", function(assert) {
    // Arrange
    var i, len, tmp;
    var currentDomain = window.location.host || "localhost";
    var _globalConfig = {
      swfPath: "ZeroClipboard.swf",
      trustedDomains: [currentDomain]
    };
    var inputToExpectedMap = [
      // Same-domain SWF
      { args: [currentDomain, _globalConfig], result: "sameDomain" },
      { args: [currentDomain, _extend({}, _globalConfig, { trustedDomains: [] })], result: "never" },
      { args: [currentDomain, _extend({}, _globalConfig, { trustedDomains: ["*"] })], result: "always" },
      { args: [currentDomain, _extend({}, _globalConfig, { trustedDomains: [currentDomain, "otherDomain.com"] })], result: "always" },
      { args: [currentDomain, _extend({}, _globalConfig, { trustedDomains: ["otherDomain.com"] })], result: "never" },
      // Cross-domain SWF
      { args: [currentDomain, _extend({}, _globalConfig, { swfPath: "//otherDomain.com/ZeroClipboard.swf" })], result: "always" },
      { args: [currentDomain, _extend({}, _globalConfig, { swfPath: "//otherDomain.com/ZeroClipboard.swf", trustedDomains: [] })], result: "never" },
      { args: [currentDomain, _extend({}, _globalConfig, { swfPath: "//otherDomain.com/ZeroClipboard.swf", trustedDomains: ["*"] })], result: "always" },
      { args: [currentDomain, _extend({}, _globalConfig, { swfPath: "//otherDomain.com/ZeroClipboard.swf", trustedDomains: [currentDomain, "otherDomain.com"] })], result: "always" }
    ];

    // Act & Assert
    assert.expect(9);
    for (i = 0, len = inputToExpectedMap.length; i < len; i++) {
      tmp = inputToExpectedMap[i];
      assert.strictEqual(_determineScriptAccess.apply(this, tmp.args), tmp.result, "Processing: " + JSON.stringify(tmp));
    }
  });


  test("`_mapClipDataToFlash` works", function(assert) {
    assert.expect(1);

    // Arrange
    var clipData = {
      "text/plain": "Zero",
      "text/html": "<b>Zero</b>"
    };
    var expectedOutput = {
      data: {
        "text": "Zero",
        "html": "<b>Zero</b>"
      },
      formatMap: {
        "text": "text/plain",
        "html": "text/html"
      }
    };

    // Act
    var actual = _mapClipDataToFlash(clipData);

    // Assert
    assert.deepEqual(actual, expectedOutput, "Converted keys to Flash-friendly names and provided a format map");
  });


  test("`_mapClipResultsFromFlash` works", function(assert) {
    assert.expect(2);

    // Arrange
    var clipResults = {
      type: "aftercopy",
      success: {
        "text": true,
        "html": false
      },
      data: {
        "text": "Zero",
        "html": "<b>Zero</b>"
      }
    };
    var formatMap = {
      "text": "text/plain",
      "html": "text/html"
    };
    var expectedOutput = {
      type: "aftercopy",
      success: {
        "text/plain": true,
        "text/html": false
      },
      data: {
        "text/plain": "Zero",
        "text/html": "<b>Zero</b>"
      }
    };

    // Act & Assert
    var thisWontChange = _mapClipResultsFromFlash(clipResults, null);
    assert.deepEqual(thisWontChange, clipResults, "Should return the original object if it cannot map it");

    // Act & Assert
    var revisedClipResults = _mapClipResultsFromFlash(clipResults, formatMap);
    assert.deepEqual(revisedClipResults, expectedOutput, "Should reverse the key mapping process");
  });


  test("`_createEvent` works", function(assert) {
    assert.expect(2);

    var actual = _createEvent("ready");

    assert.strictEqual(typeof actual === "object" && actual != null, true, "Returns non-null object");
    assert.strictEqual(actual.type, "ready", "Object has a `type` property of 'ready'");

    // etc.
  });


  // Tests fix for: https://github.com/zeroclipboard/zeroclipboard/issues/467
  test("`_copyTarget` element is handled appropriately", function(assert) {
    assert.expect(18);

    // Arrange
    var el1 = $("#d_clip_button")[0];
    var el2 = $("#goodTargetId")[0];
    _currentElement = el1;
    _copyTarget = null;

    // Act
    var evt = _createEvent("beforecopy");
    _preprocessEvent(evt);

    // Assert
    assert.strictEqual(_currentElement, el1, "`_currentElement` is 'el1'");
    assert.strictEqual(_copyTarget, el1, "`_copyTarget` is 'el1'");
    assert.strictEqual(evt.target, el1, "`beforecopy` target is 'el1'");

    // Act some more
    _currentElement = el2;
    evt = _createEvent("copy");
    _preprocessEvent(evt);

    // Assert some more
    assert.strictEqual(_currentElement, el2, "`_currentElement` is 'el2'");
    assert.strictEqual(_copyTarget, el1, "`_copyTarget` is 'el1'");
    assert.strictEqual(evt.target, el1, "`copy` target is 'el1'");

    // Act some more: interruption due to mouse movement (only happens in Firefox,
    // though similar issues occur in Chrome for Windows if the user clicks on
    // another clipped element)
    evt = _createEvent("_mouseover");
    _preprocessEvent(evt);

    // Assert some more
    assert.strictEqual(_currentElement, el2, "`_currentElement` is 'el2'");
    assert.strictEqual(_copyTarget, el1, "`_copyTarget` is 'el1'");
    assert.strictEqual(evt.target, el2, "`_mouseover` target is 'el2'");

    // Act some more
    evt = _createEvent("aftercopy");
    _preprocessEvent(evt);

    // Assert some more
    assert.strictEqual(_currentElement, el2, "`_currentElement` is 'el2'");
    assert.strictEqual(_copyTarget, el1, "`_copyTarget` is 'el1'");
    assert.strictEqual(evt.target, el1, "`aftercopy` target is 'el1'");

    // Act some more
    evt = _createEvent("_click");

    // Assert some more
    assert.strictEqual(_currentElement, el2, "`_currentElement` is 'el2'");
    assert.strictEqual(_copyTarget, el1, "`_copyTarget` is 'el1'");
    assert.strictEqual(evt.target, el1, "`_click` target is 'el1'");

    // Act some more
    _preprocessEvent(evt);

    // Assert some more
    assert.strictEqual(_currentElement, el2, "`_currentElement` is 'el2'");
    assert.strictEqual(_copyTarget, null, "`_copyTarget` is `null`");
    assert.strictEqual(evt.target, el1, "`_click` target is 'el1'");

    // Reset
    _currentElement = _copyTarget = el1 = el2 = null;
  });


  test("`_getRelatedTarget` works", function(assert) {
    assert.expect(4);

    var relTarget  = $("#relTargetId")[0];
    var goodTarget = $("#goodTargetId")[0];
    var badTarget1 = $("#badTargetId1")[0];
    var badTarget2 = $("#badTargetId2")[0];
    
    assert.notEqual(relTarget, null, "The related target is `null`");
    assert.strictEqual(_getRelatedTarget(goodTarget), relTarget, "Element with `data-clipboard-target` returns `null`");
    assert.strictEqual(_getRelatedTarget(badTarget1), null, "Element with `data-clipboard-target` that doesn't much any elements returns `null`");
    assert.strictEqual(_getRelatedTarget(badTarget2), null, "Element without `data-clipboard-target` returns `null`");
  });


  test("`_shouldPerformAsync` works", function(assert) {
    assert.expect(4);

    // Act & Assert
    assert.strictEqual(_shouldPerformAsync({ type: "beforecopy" }), false, "`beforecopy` should be performed synchronously");
    assert.strictEqual(_shouldPerformAsync({ type: "copy" }), false, "`copy` should be performed synchronously");
    assert.strictEqual(_shouldPerformAsync({ type: "destroy" }), false, "`destroy` should be performed synchronously");
    assert.strictEqual(_shouldPerformAsync({ type: "ready" }), true, "All other event types should be performed asynchronously");
  });


  test("`_dispatchCallback` can fire asynchronously", function(assert) {
    assert.expect(6);

    // Arrange
    var syncExec = false;
    var syncProof = false;
    var syncProveIt = function() {
      syncProof = true;
    };
    var asyncExec = true;
    var asyncProof = false;
    var asyncProveIt = function() {
      // Resume test evaluation
      QUnit.start();

      assert.strictEqual(asyncProof, false);
      asyncProof = true;
      assert.strictEqual(asyncProof, true);
    };

    // Act & Assert
    // Synchronous
    assert.strictEqual(syncProof, false);
    _dispatchCallback(syncProveIt, null, null, syncExec);
    assert.strictEqual(syncProof, true);

    // Asynchronous
    assert.strictEqual(asyncProof, false);
    _dispatchCallback(asyncProveIt, null, null, asyncExec);
    assert.strictEqual(asyncProof, false);

    // Stop test evaluation
    QUnit.stop();
  });


  module("core/private.js unit tests - flash", {
    setup: function() {
      flashState = _flashState;
      mimeType = window.navigator.mimeTypes["application/x-shockwave-flash"];
      ax = window.ActiveXObject;
    },
    teardown: function() {
      window.navigator.mimeTypes["application/x-shockwave-flash"] = mimeType;
      window.ActiveXObject = ax;
      _flashState = flashState;
    }
  });


  test("Detecting no Flash", function(assert) {
    assert.expect(1);

    // Arrange
    window.navigator.mimeTypes["application/x-shockwave-flash"] = undefined;
    window.ActiveXObject = undefined;

    // Act
    _detectFlashSupport(window.ActiveXObject);

    // Assert
    assert.strictEqual(_flashState.disabled, true);
  });


  test("Detecting has Flash mimetype", function(assert) {
    assert.expect(1);

    // Arrange
    window.navigator.mimeTypes["application/x-shockwave-flash"] = {};
    window.ActiveXObject = function() { };

    // Act
    _detectFlashSupport(window.ActiveXObject);

    // Assert
    assert.strictEqual(_flashState.disabled, false);
  });


})(QUnit.module, QUnit.test);
