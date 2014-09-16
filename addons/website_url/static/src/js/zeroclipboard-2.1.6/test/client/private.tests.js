/*global ZeroClipboard, _clientConstructor, _clientClip, _clientShouldEmit */

(function(module, test) {
  "use strict";

  module("client/private.js unit tests");

  test("`_clientShouldEmit` works", function(assert) {
    assert.expect(9);

    // Arrange
    var currentEl = document.getElementById("d_clip_button");
    var client = new ZeroClipboard();
    _clientConstructor.call(client);

    // Act
    var actual1 = _clientShouldEmit.call(client, null);
    var actual2 = _clientShouldEmit.call(client, {});
    var actual3 = _clientShouldEmit.call(client, { type: "beforecopy", client: {} });
    var actual4 = _clientShouldEmit.call(client, { type: "beforecopy", target: {} });
    _clientClip.call(client, currentEl);
    var actual5 = _clientShouldEmit.call(client, { type: "beforecopy", target: {}, relatedTarget: {} });
    var actual6 = _clientShouldEmit.call(client, { type: "beforecopy", client: client });
    var actual7 = _clientShouldEmit.call(client, { type: "beforecopy", target: null });
    var actual8 = _clientShouldEmit.call(client, { type: "beforecopy", target: currentEl });
    var actual9 = _clientShouldEmit.call(client, { type: "beforecopy", relatedTarget: currentEl });

    // Assert
    assert.strictEqual(actual1, false, "Non-event returns `false`");
    assert.strictEqual(actual2, false, "Event without `type` returns `false`");
    assert.strictEqual(actual3, false, "Event with non-matching `client` returns `false`");
    assert.strictEqual(actual4, false, "Event with non-clipped `target` returns `false`");
    assert.strictEqual(actual5, false, "Event with non-clipped `relatedTarget` returns `false`");
    assert.strictEqual(actual6, true, "Event with matching `client` returns `true`");
    assert.strictEqual(actual7, true, "Event with `target` of `null` returns `true`");
    assert.strictEqual(actual8, true, "Event with clipped `target` returns `true`");
    assert.strictEqual(actual9, true, "Event with clipped `relatedTarget` returns `true`");
  });

})(QUnit.module, QUnit.test);
