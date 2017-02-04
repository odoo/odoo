module('select2(data)');

var $ = require('jquery');
var Select2 = require('select2/core');
var Options = require('select2/options');

test('single default selection returned', function (assert) {
  var $select = $(
    '<select>' +
      '<option>One</option>' +
      '<option>Two</option>' +
      '<option value="3" selected>Three</option>' +
    '</select>'
  );
  var options = new Options({});

  var select = new Select2($select, options);

  var items = select.data();

  assert.equal(
    items.length,
    1,
    'The one selected item should be returned'
  );

  var first = items[0];

  assert.equal(
    first.id,
    '3',
    'The first option was correct'
  );

  assert.equal(
    first.text,
    'Three',
    'The first option was correct'
  );
});

test('multiple default selections returned', function (assert) {
  var $select = $(
    '<select multiple>' +
      '<option selected>One</option>' +
      '<option>Two</option>' +
      '<option value="3" selected>Three</option>' +
    '</select>'
  );
  var options = new Options({});

  var select = new Select2($select, options);

  var items = select.data();

  assert.equal(
    items.length,
    2,
    'The two selected items should be returned'
  );

  var first = items[0];

  assert.equal(
    first.id,
    'One',
    'The first option was correct'
  );

  var second = items[1];

  assert.equal(
    second.id,
    '3',
    'The option value should be pulled correctly'
  );
});

module('select2(val)');

test('single value matches jquery value', function (assert) {
  var $select = $(
    '<select>' +
      '<option>One</option>' +
      '<option>Two</option>' +
      '<option value="3" selected>Three</option>' +
    '</select>'
  );
  var options = new Options({});

  var select = new Select2($select, options);

  var value = select.val();

  assert.equal(
    value,
    '3',
    'The value should match the option tag attribute'
  );

  assert.equal(
    value,
    $select.val(),
    'The value should match the jquery value'
  );
});

test('multiple value matches the jquery value', function (assert) {
  var $select = $(
    '<select multiple>' +
      '<option selected>One</option>' +
      '<option>Two</option>' +
      '<option value="3" selected>Three</option>' +
    '</select>'
  );
  var options = new Options({});

  var select = new Select2($select, options);

  var value = select.val();

  assert.equal(
    value.length,
    2,
    'Two options should be selected'
  );

  assert.deepEqual(
    value,
    ['One', '3'],
    'The values should match the option tag attribute'
  );

  assert.deepEqual(
    value,
    $select.val(),
    'The values should match the jquery values'
  );
});
