/*global _document:true, _Error:true, _args, _extend, _deepCopy, _pick, _omit, _deleteOwnProperties, _containedBy, _getDirPathOfUrl, _getCurrentScriptUrlFromErrorStack, _getCurrentScriptUrlFromError:true, _getCurrentScriptUrl, _getUnanimousScriptParentDir, _getDefaultSwfPath */

(function(module, test) {
  "use strict";

  var doc, errorDef, getUrlFromError;
  module("shared/private.js unit tests", {
    setup: function() {
      doc = _document;
      errorDef = _Error;
      getUrlFromError = _getCurrentScriptUrlFromError;
    },
    teardown: function() {
      _document = doc;
      _Error = errorDef;
      _getCurrentScriptUrlFromError = getUrlFromError;
    }
  });

  test("`_args` works", function(assert) {
    assert.expect(4);

    // Arrange
    var _arguments = function() {
      return arguments;
    };
    var fn = function() {};
    var expectedOutput1 = [1, 2, 3];
    var expectedOutput2 = [fn];
    var expectedOutput3 = [{ foo: "bar" }];
    var expectedOutput4 = [[1, 2, 3]];
    var inputArgs1 = _arguments(1, 2, 3);
    var inputArgs2 = _arguments(fn);
    var inputArgs3 = _arguments({ foo: "bar" });
    var inputArgs4 = _arguments([1, 2, 3]);

    // Act
    var actualOutput1 = _args(inputArgs1);
    var actualOutput2 = _args(inputArgs2);
    var actualOutput3 = _args(inputArgs3);
    var actualOutput4 = _args(inputArgs4);

    // Arrange
    assert.deepEqual(actualOutput1, expectedOutput1);
    assert.deepEqual(actualOutput2, expectedOutput2);
    assert.deepEqual(actualOutput3, expectedOutput3);
    assert.deepEqual(actualOutput4, expectedOutput4);
  });


  test("`_extend` works on plain objects", function(assert) {
    assert.expect(5);

    // Plain objects
    var a = {
      "a": "apple",
      "c": "cantalope"
    },
    b = {
      "b": "banana",
      "c": "cherry"  // cuz cantalope sucks  ;)
    },
    c = {
      "a": "apple",
      "b": "banana",
      "c": "cherry"
    };

    assert.deepEqual(_extend({}, a), a, "actual equals expected, `target` is updated, `source` is unaffected");
    assert.deepEqual(_extend({}, b), b, "actual equals expected, `target` is updated, `source` is unaffected");
    assert.deepEqual(_extend({}, c), c, "actual equals expected, `target` is updated, `source` is unaffected");
    assert.deepEqual(_extend(a, b), c, "actual equals expected");
    assert.deepEqual(a, c, "`a` equals `c` because `_extend` updates the `target` argument");
  });


  test("`_extend` only copies owned properties", function(assert) {
    assert.expect(1);

    // Now prototypes...
    var SomeClass = function() {
      this.b = "banana";
    };
    SomeClass.prototype.c = "cantalope";  // cuz cantalope sucks  ;)

    var a = {
      "a": "apple",
      "c": "cherry"
    },
    b = new SomeClass(),
    c = {
      "a": "apple",
      "b": "banana",
      "c": "cherry"
    };

    assert.deepEqual(_extend(a, b), c, "actual equals expected because `_extend` does not copy over prototype properties");
  });


  test("`_extend` only copies owned properties from Array source", function(assert) {
    assert.expect(3);

    var a = {
      "a": "apple",
      "b": "banana"
    },
    b = ["zero", "one", "two"],
    c = {
      "a": "apple",
      "b": "banana",
      "0": "zero",
      "1": "one",
      "2": "two"
    };

    assert.deepEqual(_extend(a, b), c, "actual equals expected because `_extend` does not copy over prototype properties");
    assert.strictEqual("length" in a, false, "`a` should not have gained a `length` property");
    assert.strictEqual("length" in b, true, "`b` should still have a `length` property");
  });


  test("`_extend` will merge multiple objects", function(assert) {
    assert.expect(2);

    var a = {
      "a": "apple",
      "c": "cantalope",
      "d": "dragon fruit"
    },
    b = {
      "b": "banana",
      "c": "cherry"  // cuz cantalope sucks  ;)
    },
    c = {
      "a": "apricot",
      "b": "blueberry"
    },
    d = {
      "a": "apricot",
      "b": "blueberry",
      "c": "cherry",
      "d": "dragon fruit"
    };

    assert.deepEqual(_extend({}, a, b, c), d, "actual equals expected, `target` is updated, `source` is unaffected");
    assert.deepEqual(_extend(a, b, c), d, "actual equals expected");
  });


  test("`_deepCopy` works", function(assert) {
    assert.expect(13);

    // Arrange
    var input1 = {
      "a": "b",
      "b": {
        "c": "d"
      }
    };
    var input2 = [[1, 2], 2];
    var expected1 = {
      "a": "b",
      "b": {
        "c": "d"
      }
    };
    var expected2 = [[1, 2], 2];

    // Act
    var actual1 = _deepCopy(input1);
    var actual2 = _deepCopy(input2);

    // Assert
    assert.deepEqual(actual1, expected1, "Objects are deeply equal");
    assert.notStrictEqual(actual1, expected1, "Objects are not strictly equal");
    assert.strictEqual(actual1.a, expected1.a, "Objects' non-object properties are strictly equal");
    assert.deepEqual(actual1.b, expected1.b, "Objects' object properties are deeply equal");
    assert.notStrictEqual(actual1.b, expected1.b, "Objects' object properties are not strictly equal");
    assert.strictEqual(actual1.b.c, expected1.b.c, "Objects' object properties' non-object properties are strictly equal");

    assert.deepEqual(actual2, expected2, "Arrays are deeply equal");
    assert.notStrictEqual(actual2, expected2, "Arrays are not strictly equal");
    assert.deepEqual(actual2[0], expected2[0], "Sub-arrays are deeply equal");
    assert.notStrictEqual(actual2[0], expected2[0], "Sub-arrays are not strictly equal");
    assert.strictEqual(actual2[0][0], expected2[0][0], "Sub-arrays' first items are strictly equal");
    assert.strictEqual(actual2[0][1], expected2[0][1], "Sub-arrays' second items are strictly equal");
    assert.strictEqual(actual2[1], expected2[1], "Sub-items are strictly equal");
  });


  test("`_pick` works", function(assert) {
    assert.expect(6);

    // Arrange
    var obj1 = {};
    var obj2 = {
      "name": "Zero",
      "version": "v2.x",
      "other": "test"
    };
    var filter1 = [];
    var filter2 = ["name", "version"];
    var filter3 = ["name", "version", "other"];

    var expected1x = {};
    var expected21 = {};
    var expected22 = {
      "name": "Zero",
      "version": "v2.x"
    };
    var expected23 = {
      "name": "Zero",
      "version": "v2.x",
      "other": "test"
    };

    // Act
    var result11 = _pick(obj1, filter1);
    var result12 = _pick(obj1, filter2);
    var result13 = _pick(obj1, filter3);
    var result21 = _pick(obj2, filter1);
    var result22 = _pick(obj2, filter2);
    var result23 = _pick(obj2, filter3);

    // Assert
    assert.deepEqual(result11, expected1x, "An empty object cannot have any properties picked");
    assert.deepEqual(result12, expected1x, "An empty object cannot have any properties picked");
    assert.deepEqual(result13, expected1x, "An empty object cannot have any properties picked");
    assert.deepEqual(result21, expected21, "An object with an empty pick list will have nothing picked");
    assert.deepEqual(result22, expected22, "An object with a subset pick list will have only those properties picked");
    assert.deepEqual(result23, expected23, "An object with a complete pick list will have all of its properties picked");
  });


  test("`_omit` works", function(assert) {
    assert.expect(6);

    // Arrange
    var obj1 = {};
    var obj2 = {
      "name": "Zero",
      "version": "v2.x",
      "other": "test"
    };
    var filter1 = [];
    var filter2 = ["name", "version"];
    var filter3 = ["name", "version", "other"];

    var expected1x = {};
    var expected21 = {
      "name": "Zero",
      "version": "v2.x",
      "other": "test"
    };
    var expected22 = {
      "other": "test"
    };
    var expected23 = {};

    // Act
    var result11 = _omit(obj1, filter1);
    var result12 = _omit(obj1, filter2);
    var result13 = _omit(obj1, filter3);
    var result21 = _omit(obj2, filter1);
    var result22 = _omit(obj2, filter2);
    var result23 = _omit(obj2, filter3);

    // Assert
    assert.deepEqual(result11, expected1x, "An empty object cannot have any properties picked");
    assert.deepEqual(result12, expected1x, "An empty object cannot have any properties picked");
    assert.deepEqual(result13, expected1x, "An empty object cannot have any properties picked");
    assert.deepEqual(result21, expected21, "An object with an empty omit list will have everything picked");
    assert.deepEqual(result22, expected22, "An object with a subset omit list will have everything but those properties picked");
    assert.deepEqual(result23, expected23, "An object with a complete omit list will have nothing picked");
  });


  test("`_deleteOwnProperties` will delete all owned enumerable properties", function(assert) {
    assert.expect(24);

    var getNonObjectKeys = function(obj) {
      var prop,
          keys = [];
      if (obj) {
        for (prop in obj) {
          if (obj.hasOwnProperty(prop)) {
            keys.push(prop);
          }
        }
      }
      return keys;
    };
    var getProtoKeys = function(obj) {
      var prop,
          keys = [];
      if (obj) {
        for (prop in obj) {
          if (!obj.hasOwnProperty(prop)) {
            keys.push(prop);
          }
        }
      }
      return keys;
    };

    var a = {
      "a": "apple",
      "c": "cantalope",
      "d": "dragon fruit"
    },
    b = {},
    c = ["banana", "cherry"],
    d = (function() {
      function SomePrototype() {
        this.protoProp = "foo";
      }
      function SomeClass() {
        this.ownedProp = "bar";
      }
      SomeClass.prototype = new SomePrototype();
      SomeClass.prototype.constructor = SomeClass;

      return new SomeClass();
    })(),
    e = null,
    f; // = undefined;

    assert.deepEqual(Object.keys(a), ["a", "c", "d"]);
    assert.deepEqual(getProtoKeys(a), []);
    _deleteOwnProperties(a);
    assert.deepEqual(Object.keys(a), []);
    assert.deepEqual(getProtoKeys(a), []);

    assert.deepEqual(Object.keys(b), []);
    assert.deepEqual(getProtoKeys(b), []);
    _deleteOwnProperties(b);
    assert.deepEqual(Object.keys(b), []);
    assert.deepEqual(getProtoKeys(b), []);

    assert.deepEqual(getNonObjectKeys(c), ["0", "1"]);
    assert.deepEqual(getProtoKeys(c), []);
    _deleteOwnProperties(c);
    assert.deepEqual(getNonObjectKeys(c), []);
    assert.deepEqual(getProtoKeys(c), []);

    assert.deepEqual(Object.keys(d), ["ownedProp"]);
    assert.deepEqual(getProtoKeys(d), ["protoProp", "constructor"]);
    _deleteOwnProperties(d);
    assert.deepEqual(Object.keys(d), []);
    assert.deepEqual(getProtoKeys(d), ["protoProp", "constructor"]);

    assert.deepEqual(getNonObjectKeys(e), []);
    assert.deepEqual(getProtoKeys(e), []);
    _deleteOwnProperties(e);
    assert.deepEqual(getNonObjectKeys(e), []);
    assert.deepEqual(getProtoKeys(e), []);

    assert.deepEqual(getNonObjectKeys(f), []);
    assert.deepEqual(getProtoKeys(f), []);
    _deleteOwnProperties(f);
    assert.deepEqual(getNonObjectKeys(f), []);
    assert.deepEqual(getProtoKeys(f), []);
  });


  test("`_containedBy` works", function(assert) {
    /*jshint camelcase:false */

    assert.expect(29);

    // Arrange
    var fixture = document.getElementById("qunit-fixture");
    fixture.innerHTML =
      "<div id='container'>" +
        "<div id='contained1'>" +
          "<div id='contained1_1'></div>" +
          "<div id='contained1_2'>" +
            "<div id='contained1_2_1'></div>" +
          "</div>" +
        "</div>" +
        "<div id='contained2'></div>" +
      "</div>" +
      "<div id='not_container'>" +
        "<div id='not_contained'></div>" +
      "</div>";

    var container = document.getElementById("container");
    var contained1 = document.getElementById("contained1");
    var contained1_1 = document.getElementById("contained1_1");
    var contained1_2 = document.getElementById("contained1_2");
    var contained1_2_1 = document.getElementById("contained1_2_1");
    var contained2 = document.getElementById("contained2");
    var not_container = document.getElementById("not_container");
    var not_contained = document.getElementById("not_contained");

    // Act & Assert
    assert.strictEqual(_containedBy(contained1_2_1, contained1_2_1), true);
    assert.strictEqual(_containedBy(contained1_2_1, contained1_2), true);
    assert.strictEqual(_containedBy(contained1_2_1, contained1), true);
    assert.strictEqual(_containedBy(contained1_2_1, container), true);
    assert.strictEqual(_containedBy(contained1_2_1, fixture), true);
    assert.strictEqual(_containedBy(contained1_2_1, not_container), false);

    assert.strictEqual(_containedBy(contained1_1, contained1_1), true);
    assert.strictEqual(_containedBy(contained1_1, contained1), true);
    assert.strictEqual(_containedBy(contained1_1, container), true);
    assert.strictEqual(_containedBy(contained1_1, fixture), true);
    assert.strictEqual(_containedBy(contained1_1, not_container), false);

    assert.strictEqual(_containedBy(contained1, contained1), true);
    assert.strictEqual(_containedBy(contained1, container), true);
    assert.strictEqual(_containedBy(contained1, fixture), true);
    assert.strictEqual(_containedBy(contained1, not_container), false);

    assert.strictEqual(_containedBy(contained2, contained2), true);
    assert.strictEqual(_containedBy(contained2, container), true);
    assert.strictEqual(_containedBy(contained2, fixture), true);
    assert.strictEqual(_containedBy(contained2, not_container), false);

    assert.strictEqual(_containedBy(container, container), true);
    assert.strictEqual(_containedBy(container, fixture), true);
    assert.strictEqual(_containedBy(container, not_container), false);

    assert.strictEqual(_containedBy(not_contained, not_contained), true);
    assert.strictEqual(_containedBy(not_contained, not_container), true);
    assert.strictEqual(_containedBy(not_contained, fixture), true);
    assert.strictEqual(_containedBy(not_contained, container), false);

    assert.strictEqual(_containedBy(not_container, not_container), true);
    assert.strictEqual(_containedBy(not_container, fixture), true);
    assert.strictEqual(_containedBy(not_container, container), false);
  });


  test("`_getDirPathOfUrl` works", function(assert) {
    assert.expect(8);

    // Arrange
    var input1 = "http://example.com/blah/foo/index.html";
    var input2 = "http://example.com/blah/foo/index.html?q=p";
    var input3 = "http://example.com/blah/foo/index.html?q=p&x=z";
    var input4 = "http://example.com/blah/foo/index.html?#xyz";
    var input5 = "http://example.com/blah/foo/index.html?q=p#xyz";
    var input6 = "http://example.com/blah/foo/index.html?q=p&x=z#xyz";
    var input7 = "http://example.com/blah/foo/";
    var input8 = "";
    var expected1 = "http://example.com/blah/foo/";
    var expected2 = "http://example.com/blah/foo/";
    var expected3 = "http://example.com/blah/foo/";
    var expected4 = "http://example.com/blah/foo/";
    var expected5 = "http://example.com/blah/foo/";
    var expected6 = "http://example.com/blah/foo/";
    var expected7 = "http://example.com/blah/foo/";
    var expected8;

    // Act
    var actual1 = _getDirPathOfUrl(input1);
    var actual2 = _getDirPathOfUrl(input2);
    var actual3 = _getDirPathOfUrl(input3);
    var actual4 = _getDirPathOfUrl(input4);
    var actual5 = _getDirPathOfUrl(input5);
    var actual6 = _getDirPathOfUrl(input6);
    var actual7 = _getDirPathOfUrl(input7);
    var actual8 = _getDirPathOfUrl(input8);

    // Assert
    assert.strictEqual(actual1, expected1);
    assert.strictEqual(actual2, expected2);
    assert.strictEqual(actual3, expected3);
    assert.strictEqual(actual4, expected4);
    assert.strictEqual(actual5, expected5);
    assert.strictEqual(actual6, expected6);
    assert.strictEqual(actual7, expected7);
    assert.strictEqual(actual8, expected8);
  });


  test("`_getCurrentScriptUrlFromErrorStack` works", function(assert) {
    assert.expect(25);

    // Arrange
    var localStacks = [
      "Error: my uncaught error\n    at http://example.com/index.html:123:4\n    at jQuery.event.dispatch (http://code.jquery.com/blah.js:567:8)\n    at foo",
      "http://example.com/index.html:123:4\ndispatch@http://code.jquery.com/blah.js:567:8\nfoo",
      "@http://example.com/index.html:123\ndispatch@http://code.jquery.com/blah.js:567\nfoo",
      "<anonymous function>([arguments not available])@http://example.com/index.html:123\n<anonymous function: dispatch>([arguments not available])@http://code.jquery.com/blah.js:567\nfoo",
      "Error: my error\n    at http://example.com/index.html:123\n    at http://code.jquery.com/blah.js:567\nfoo",
      "Error(\"my error\")@:0\u000a([object Object])@http://example.com/index.html:123\u000a([object Object])@http://code.jquery.com/blah.js:567\u000afoo",
      "Error: my error\n    at Anonymous function (http://example.com/index.html:123:4)\n    at dispatch (http://code.jquery.com/blah.js:567:8)\n    at foo",
      "Error: my sneaky error message has a URL in it at http://google.com/mean.js:987\n    at Anonymous function (http://example.com/index.html:123:4)\n    at dispatch (http://code.jquery.com/blah.js:567:8)\n    at foo"
    ];
    var remoteStacks = [
      "Error: my error\n    at window.onload (http://example.com/blah/foo.js:95:11)\n    at jQuery.event.dispatch (http://code.jquery.com/blah.js:567:8)\n    at foo",
      "onload@http://example.com/blah/foo.js:95:11\ndispatch@http://code.jquery.com/blah.js:567:8\nfoo",
      "onload@http://example.com/blah/foo.js:95\ndispatch@http://code.jquery.com/blah.js:567\nfoo",
      "<anonymous function: window.onload>([arguments not available])@http://example.com/blah/foo.js:95\n<anonymous function: dispatch>([arguments not available])@http://code.jquery.com/blah.js:567\nfoo",
      "Error: my error\n    at http://example.com/blah/foo.js:95\n    at http://code.jquery.com/blah.js:567\nfoo",
      "Error(\"my error\")@:0\u000a@http://example.com/blah/foo.js:95\u000a([object Object])@http://code.jquery.com/blah.js:567\u000afoo",
      "Error: my error\n    at onload (http://example.com/blah/foo.js:95:11)\n    at dispatch (http://code.jquery.com/blah.js:567:8)\n    at foo",
      "Error: my sneaky error message has a URL in it at http://google.com/mean.js:987\n    at onload (http://example.com/blah/foo.js:95:11)\n    at dispatch (http://code.jquery.com/blah.js:567:8)\n    at foo"
    ];
    var badStacks = [
      "blah",
      "",
      [],
      {},
      null,
      undefined
    ];
    var localExpected = "http://example.com/index.html",
        remoteExpected = "http://example.com/blah/foo.js",
        badExpected;

    // Act & Assert
    assert.strictEqual(localStacks.length, 8, "Local stacks x 8");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(localStacks[0]), localExpected, "Inline script: Chrome");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(localStacks[1]), localExpected, "Inline script: Safari 6.1+");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(localStacks[2]), localExpected, "Inline script: Safari 6.0");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(localStacks[3]), localExpected, "Inline script: Opera");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(localStacks[4]), localExpected, "Inline script: PhantomJS");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(localStacks[5]), localExpected, "Inline script: Firefox 3.6");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(localStacks[6]), localExpected, "Inline script: IE 10.0");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(localStacks[7]), localExpected, "Inline script: SneakyError");

    assert.strictEqual(remoteStacks.length, 8, "Remote stacks x 8");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(remoteStacks[0]), remoteExpected, "External script: Chrome");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(remoteStacks[1]), remoteExpected, "External script: Safari 6.1+");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(remoteStacks[2]), remoteExpected, "External script: Safari 6.0");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(remoteStacks[3]), remoteExpected, "External script: Opera");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(remoteStacks[4]), remoteExpected, "External script: PhantomJS");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(remoteStacks[5]), remoteExpected, "External script: Firefox 3.6");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(remoteStacks[6]), remoteExpected, "External script: IE 10.0");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(remoteStacks[7]), remoteExpected, "External script: SneakyError");

    assert.strictEqual(badStacks.length, 6, "Bad stacks x 6");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(badStacks[0]), badExpected, "Useless stack");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(badStacks[1]), badExpected, "Empty string");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(badStacks[2]), badExpected, "Array");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(badStacks[3]), badExpected, "Object");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(badStacks[4]), badExpected, "`null`");
    assert.strictEqual(_getCurrentScriptUrlFromErrorStack(badStacks[5]), badExpected, "`undefined`");
  });


  test("`_getCurrentScriptUrlFromError` works", function(assert) {
    assert.expect(4);

    // Arrange
    var actual1, actual2, actual3, actual4;
    var expected = "http://example.com/blah/foo.js";
    var _sourceUrl, _fileName, _stack;

    // Do NOT inherit from the real `Error` definition
    _Error = function() {
      this.sourceURL = _sourceUrl;
      this.fileName = _fileName;
      this.stack = _stack;
    };

    // Act
    _sourceUrl = expected;
    _fileName = undefined;
    _stack = undefined;
    actual1 = _getCurrentScriptUrlFromError();

    _sourceUrl = undefined;
    _fileName = expected;
    _stack = undefined;
    actual2 = _getCurrentScriptUrlFromError();

    _sourceUrl = undefined;
    _fileName = undefined;
    _stack = "Error: my uncaught error\n    at " + expected + ":123:4\n    at jQuery.event.dispatch (http://code.jquery.com/blah.js:123:0)\n    at foo";
    actual3 = _getCurrentScriptUrlFromError();

    _sourceUrl = undefined;
    _fileName = undefined;
    _stack = undefined;
    actual4 = _getCurrentScriptUrlFromError();

    // Assert
    assert.strictEqual(actual1, expected, "Current script derived from `err.sourceURL`");
    assert.strictEqual(actual2, expected, "Current script derived from `err.fileName`");
    assert.strictEqual(actual3, expected, "Current script derived from `err.stack`");
    assert.strictEqual(actual4, undefined, "Current script cannot be derived from the Error");
  });


  test("`_getCurrentScriptUrl` works", function(assert) {
    assert.expect(9);

    // Arrange
    var actual1, actual2, actual3, actual4, actual5, actual6, actual7, actual8, actual9;
    var expected1, expected2, expected3, expected4, expected5, expected6, expected7, expected8, expected9;
    expected1 = expected2 = expected3 = expected4 = expected5 = "http://example.com/blah/foo/bar.js";

    // Arrange & Act
    _document = {
      currentScript: {
        src: "http://example.com/blah/foo/bar.js"
      }
    };
    _getCurrentScriptUrlFromError = function() {};
    actual1 = _getCurrentScriptUrl();

    _document = {
      getElementsByTagName: function(/* tagName */)  {
        return [
          { src: "http://example.com/blah/foo/bar.js" }
        ];
      }
    };
    actual2 = _getCurrentScriptUrl();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js", readyState: "complete" },
          { src: "http://example.com/blah/foo/bar.js", readyState: "interactive" }
        ];
      }
    };
    actual3 = _getCurrentScriptUrl();

    _document = {
      readyState: "loading",
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js" },
          { src: "http://example.com/blah/wat.js" },
          { src: "http://example.com/blah/foo/bar.js" }
        ];
      }
    };
    actual4 = _getCurrentScriptUrl();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js" },
          { src: "http://example.com/blah/wat.js" },
          { src: "http://example.com/blah/foo/bar.js" }
        ];
      }
    };
    _getCurrentScriptUrlFromError = function() {
      return "http://example.com/blah/foo/bar.js";
    };
    actual5 = _getCurrentScriptUrl();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js" },
          { src: "http://example.com/blah/wat.js" }
        ];
      }
    };
    _getCurrentScriptUrlFromError = function() {};
    actual6 = _getCurrentScriptUrl();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js" },
          { /* inline script */ },
          { src: "http://example.com/blah/wat.js" }
        ];
      }
    };
    actual7 = _getCurrentScriptUrl();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js" },
          { src: "http://example.com/blah/wat.js" },
          { /* inline script */ }
        ];
      }
    };
    actual8 = _getCurrentScriptUrl();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { /* inline script */ }
        ];
      }
    };
    actual9 = _getCurrentScriptUrl();

    assert.strictEqual(actual1, expected1, "Value from `document.currentScript`");
    assert.strictEqual(actual2, expected2, "Value from the only script");
    assert.strictEqual(actual3, expected3, "Value from `scripts[i].readyState === \"interactive\"`");
    assert.strictEqual(actual4, expected4, "Value from last script while `document.readyState === \"loading\"");
    assert.strictEqual(actual5, expected5, "Value from `_getCurrentScriptUrlFromError`");
    assert.strictEqual(actual6, expected6, "No value can be confirmed");
    assert.strictEqual(actual7, expected7, "No value can be confirmed as there is at least one inline script (middle)");
    assert.strictEqual(actual8, expected8, "No value can be confirmed as there is at least one inline script (last)");
    assert.strictEqual(actual9, expected9, "No value can be confirmed as the only script tag is an inline script");
  });


  test("`_getUnanimousScriptParentDir` works", function(assert) {
    assert.expect(5);

    // Arrange
    var actual1, actual2, actual3, actual4, actual5;
    var expected1, expected2, expected3, expected4, expected5;
    var _scripts = [];
    _document = {
      getElementsByTagName: function(/* tagName */) {
        return _scripts;
      }
    };
    expected1 = "http://example.com/blah/";

    // Arrange & Act
    _scripts.length = 0;
    _scripts.push.apply(_scripts, [
      { src: "http://example.com/blah/foo.js" },
      { src: "http://example.com/blah/wat.js" },
      { src: "http://example.com/blah/bar.js" }
    ]);
    actual1 = _getUnanimousScriptParentDir();

    _scripts.length = 0;
    _scripts.push.apply(_scripts, [
      { src: "http://example.org/blah/foo.js" },
      { src: "http://example.net/blah/wat.js" },
      { src: "http://example.com/blah/bar.js" }
    ]);
    actual2 = _getUnanimousScriptParentDir();

    _scripts.length = 0;
    _scripts.push.apply(_scripts, [
      { src: "http://example.com/blah/foo.js" },
      { src: "http://example.com/blah/wat.js" },
      { src: "http://example.com/blah/foo/bar.js" }
    ]);
    actual3 = _getUnanimousScriptParentDir();

    _scripts.length = 0;
    _scripts.push.apply(_scripts, [
      { src: "http://example.com/blah/foo.js" },
      { /* inline script */ },
      { src: "http://example.com/blah/foo/bar.js" }
    ]);
    actual4 = _getUnanimousScriptParentDir();

    _scripts.length = 0;
    _scripts.push.apply(_scripts, [
      { src: "http://example.com/blah/foo.js" },
      { src: "http://example.com/blah/wat.js" },
      { /* inline script */ }
    ]);
    actual5 = _getUnanimousScriptParentDir();

    // Assert
    assert.strictEqual(actual1, expected1, "All script tags have the same parent directory");
    assert.strictEqual(actual2, expected2, "Not all script tags have the same domains");
    assert.strictEqual(actual3, expected3, "Not all script tags have the same parent directory");
    assert.strictEqual(actual4, expected4, "Not all script tags have `src` URLs (middle)");
    assert.strictEqual(actual5, expected5, "Not all script tags have `src` URLs (last)");
  });


  test("`_getDefaultSwfPath` works", function(assert) {
    assert.expect(11);

    // Arrange
    var actual1, actual2, actual3, actual4, actual5, actual6, actual7, actual8, actual9, actual10, actual11;
    var expected1, expected2, expected3, expected4, expected5, expected6, expected7, expected8, expected9, expected10, expected11;
    expected1 = expected2 = expected3 = expected4 = expected5 = "http://example.com/blah/foo/ZeroClipboard.swf";
    expected6 = "http://example.com/blah/ZeroClipboard.swf";
    expected7 = expected8 = expected9 = expected10 = expected11 = "ZeroClipboard.swf";

    // Arrange & Act
    _document = {
      currentScript: {
        src: "http://example.com/blah/foo/bar.js"
      }
    };
    actual1 = _getDefaultSwfPath();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo/bar.js" }
        ];
      }
    };
    actual2 = _getDefaultSwfPath();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js", readyState: "complete" },
          { src: "http://example.com/blah/foo/bar.js", readyState: "interactive" }
        ];
      }
    };
    actual3 = _getDefaultSwfPath();

    _document = {
      readyState: "loading",
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js" },
          { src: "http://example.com/blah/wat.js" },
          { src: "http://example.com/blah/foo/bar.js" }
        ];
      }
    };
    actual4 = _getDefaultSwfPath();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js" },
          { src: "http://example.com/blah/wat.js" },
          { src: "http://example.com/blah/foo/bar.js" }
        ];
      }
    };
    _getCurrentScriptUrlFromError = function() {
      return "http://example.com/blah/foo/bar.js";
    };
    actual5 = _getDefaultSwfPath();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js" },
          { src: "http://example.com/blah/wat.js" },
          { src: "http://example.com/blah/bar.js" }
        ];
      }
    };
    _getCurrentScriptUrlFromError = function() {};
    actual6 = _getDefaultSwfPath();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.org/blah/foo.js" },
          { src: "http://example.net/blah/wat.js" },
          { src: "http://example.com/blah/bar.js" }
        ];
      }
    };
    actual7 = _getDefaultSwfPath();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js" },
          { src: "http://example.com/blah/wat.js" },
          { src: "http://example.com/blah/foo/bar.js" }
        ];
      }
    };
    actual8 = _getDefaultSwfPath();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js" },
          { /* inline script */ },
          { src: "http://example.com/blah/foo/bar.js" }
        ];
      }
    };
    actual9 = _getDefaultSwfPath();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { src: "http://example.com/blah/foo.js" },
          { src: "http://example.com/blah/wat.js" },
          { /* inline script */ }
        ];
      }
    };
    actual10 = _getDefaultSwfPath();

    _document = {
      getElementsByTagName: function(/* tagName */) {
        return [
          { /* inline script */ }
        ];
      }
    };
    actual11 = _getDefaultSwfPath();

    assert.strictEqual(actual1, expected1, "Value derived from `document.currentScript`");
    assert.strictEqual(actual2, expected2, "Value derived from the only script");
    assert.strictEqual(actual3, expected3, "Value derived from `scripts[i].readyState === \"interactive\"`");
    assert.strictEqual(actual4, expected4, "Value derived from last script while `document.readyState === \"loading\"");
    assert.strictEqual(actual5, expected5, "Value derived from Error stack");
    assert.strictEqual(actual6, expected6, "Value derived from confirming all scripts have the same parent directory");
    assert.strictEqual(actual7, expected7, "No value can be confirmed due to differing script domains");
    assert.strictEqual(actual8, expected8, "No value can be confirmed due to differing script parent directories");
    assert.strictEqual(actual9, expected9, "No value can be confirmed due to the existence of inline scripts");
    assert.strictEqual(actual10, expected10, "No value can be confirmed as the last script is an inline script");
    assert.strictEqual(actual11, expected11, "No value can be confirmed as the only script is an inline script");
  });

})(QUnit.module, QUnit.test);
