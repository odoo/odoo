/*
 * Copyright 2012 The Polymer Authors. All rights reserved.
 * Use of this source code is governed by a BSD-style
 * license that can be found in the LICENSE file.
 */

suite('JsMutationObserver callback', function() {

  test('One observer, two attribute changes', function(cont) {
    var div = document.createElement('div');
    var observer = new JsMutationObserver(function(records) {
      assert.strictEqual(records.length, 2);

      expectRecord(records[0], {
        type: 'attributes',
        target: div,
        attributeName: 'a',
        attributeNamespace: null
      });
      expectRecord(records[1], {
        type: 'attributes',
        target: div,
        attributeName: 'a',
        attributeNamespace: null
      });

      cont();
    });

    observer.observe(div, {
      attributes: true
    });

    div.setAttribute('a', 'A');
    div.setAttribute('a', 'B');
  });

  test('nested changes', function(cont) {
    var div = document.createElement('div');
    var i = 0;
    var observer = new JsMutationObserver(function(records) {
      assert.strictEqual(records.length, 1);

      if (i === 0) {
        expectRecord(records[0], {
          type: 'attributes',
          target: div,
          attributeName: 'a',
          attributeNamespace: null
        });
        div.setAttribute('b', 'B');
        i++;
      } else {
        expectRecord(records[0], {
          type: 'attributes',
          target: div,
          attributeName: 'b',
          attributeNamespace: null
        });

        cont();
      }
    });

    observer.observe(div, {
      attributes: true
    });

    div.setAttribute('a', 'A');
  });

});