/*
 * Copyright 2012 The Polymer Authors. All rights reserved.
 * Use of this source code is governed by a BSD-style
 * license that can be found in the LICENSE file.
 */

suite('JsMutationObserver transient', function() {

  var testDiv;

  setup(function() {
    testDiv = document.body.appendChild(document.createElement('div'));
  });

  teardown(function() {
    document.body.removeChild(testDiv);
  });

  test('attr', function() {
    var div = testDiv.appendChild(document.createElement('div'));
    var child = div.appendChild(document.createElement('div'));
    var observer = new JsMutationObserver(function() {});
    observer.observe(div, {
      attributes: true,
      subtree: true
    });
    div.removeChild(child);
    child.setAttribute('a', 'A');

    var records = observer.takeRecords();
    assert.strictEqual(records.length, 1);

    expectRecord(records[0], {
      type: 'attributes',
      target: child,
      attributeName: 'a',
      attributeNamespace: null
    });

    child.setAttribute('b', 'B');

    records = observer.takeRecords();
    assert.strictEqual(records.length, 1);

    expectRecord(records[0], {
      type: 'attributes',
      target: child,
      attributeName: 'b',
      attributeNamespace: null
    });
  });

  test('attr callback', function(cont) {
    var div = testDiv.appendChild(document.createElement('div'));
    var child = div.appendChild(document.createElement('div'));
    var i = 0;
    var observer = new JsMutationObserver(function(records) {
      i++;
      if (i > 1)
        expect().fail();

      assert.strictEqual(records.length, 1);

      expectRecord(records[0], {
        type: 'attributes',
        target: child,
        attributeName: 'a',
        attributeNamespace: null
      });

      // The transient observers are removed before the callback is called.
      child.setAttribute('b', 'B');
      records = observer.takeRecords();
      assert.strictEqual(records.length, 0);

      cont();
    });

    observer.observe(div, {
      attributes: true,
      subtree: true
    });

    div.removeChild(child);
    child.setAttribute('a', 'A');
  });

  test('attr, make sure transient gets removed', function(cont) {
    var div = testDiv.appendChild(document.createElement('div'));
    var child = div.appendChild(document.createElement('div'));
    var i = 0;
    var observer = new JsMutationObserver(function(records) {
      i++;
      if (i > 1)
        expect().fail();

      assert.strictEqual(records.length, 1);

      expectRecord(records[0], {
        type: 'attributes',
        target: child,
        attributeName: 'a',
        attributeNamespace: null
      });

      step2();
    });

    observer.observe(div, {
      attributes: true,
      subtree: true
    });

    div.removeChild(child);
    child.setAttribute('a', 'A');

    function step2() {
      var div2 = document.createElement('div');
      var observer2 = new JsMutationObserver(function(records) {
        i++;
        if (i > 2)
          expect().fail();

        assert.strictEqual(records.length, 1);

        expectRecord(records[0], {
          type: 'attributes',
          target: child,
          attributeName: 'b',
          attributeNamespace: null
        });

        cont();
      });

      observer2.observe(div2, {
        attributes: true,
        subtree: true,
      });

      div2.appendChild(child);
      child.setAttribute('b', 'B');
    }
  });

  test('characterData', function() {
    var div = document.createElement('div');
    var child = div.appendChild(document.createTextNode('text'));
    var observer = new JsMutationObserver(function() {});
    observer.observe(div, {
      characterData: true,
      subtree: true
    });
    div.removeChild(child);
    child.data = 'changed';

    var records = observer.takeRecords();
    assert.strictEqual(records.length, 1);

    expectRecord(records[0], {
      type: 'characterData',
      target: child
    });

    child.data += ' again';

    records = observer.takeRecords();
    assert.strictEqual(records.length, 1);

    expectRecord(records[0], {
      type: 'characterData',
      target: child
    });
  });

  test('characterData callback', function(cont) {
    var div = document.createElement('div');
    var child = div.appendChild(document.createTextNode('text'));
    var i = 0;
    var observer = new JsMutationObserver(function(records) {
      i++;
      if (i > 1)
        expect().fail();

      assert.strictEqual(records.length, 1);

      expectRecord(records[0], {
        type: 'characterData',
        target: child
      });

      // The transient observers are removed before the callback is called.
      child.data += ' again';
      records = observer.takeRecords();
      assert.strictEqual(records.length, 0);

      cont();
    });
    observer.observe(div, {
      characterData: true,
      subtree: true
    });
    div.removeChild(child);
    child.data = 'changed';
  });

  test('childList', function() {
    var div = testDiv.appendChild(document.createElement('div'));
    var child = div.appendChild(document.createElement('div'));
    var observer = new JsMutationObserver(function() {});
    observer.observe(div, {
      childList: true,
      subtree: true
    });
    div.removeChild(child);
    var grandChild = child.appendChild(document.createElement('span'));

    var records = observer.takeRecords();
    assert.strictEqual(records.length, 2);

    expectRecord(records[0], {
      type: 'childList',
      target: div,
      removedNodes: [child]
    });

    expectRecord(records[1], {
      type: 'childList',
      target: child,
      addedNodes: [grandChild]
    });

    child.removeChild(grandChild);

    records = observer.takeRecords();
    assert.strictEqual(records.length, 1);

    expectRecord(records[0], {
      type: 'childList',
      target: child,
      removedNodes: [grandChild]
    });
  });

  test('childList callback', function(cont) {
    var div = testDiv.appendChild(document.createElement('div'));
    var child = div.appendChild(document.createElement('div'));
    var i = 0;
    var observer = new JsMutationObserver(function(records) {
      i++;
      if (i > 1)
        expect().fail();

      assert.strictEqual(records.length, 2);

      expectRecord(records[0], {
        type: 'childList',
        target: div,
        removedNodes: [child]
      });

      expectRecord(records[1], {
        type: 'childList',
        target: child,
        addedNodes: [grandChild]
      });

      // The transient observers are removed before the callback is called.
      child.removeChild(grandChild);

      records = observer.takeRecords();
      assert.strictEqual(records.length, 0);

      cont();
    });
    observer.observe(div, {
      childList: true,
      subtree: true
    });
    div.removeChild(child);
    var grandChild = child.appendChild(document.createElement('span'));
  });
});
