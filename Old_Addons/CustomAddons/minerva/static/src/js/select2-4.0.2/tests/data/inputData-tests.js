module('Data adapters - <input> compatibility');

var $ = require('jquery');

var Options = require('select2/options');
var Utils = require('select2/utils');

var ArrayData = require('select2/data/array');
var InputData = require('select2/compat/inputData');

var InputAdapter = Utils.Decorate(ArrayData, InputData);

test('test that options can be selected', function (assert) {
  var options = new Options({
    data: [
      {
        id: 'test',
        text: 'Test'
      }
    ]
  });
  var $element = $('<input />');

  var adapter = new InputAdapter($element, options);

  adapter.select({
    id: 'test'
  });

  assert.equal(
    $element.val(),
    'test',
    'The id of the item should be the value'
  );
});

test('unselect the single selected option clears the value', function (assert) {
  var options = new Options({
    data: [
      {
        id: 'test',
        text: 'Test',
        selected: true
      }
    ]
  });
  var $element = $('<input />');

  var adapter = new InputAdapter($element, options);

  adapter.unselect({
    id: 'test'
  });

  assert.equal(
    $element.val(),
    '',
    'The id should no longer be in the value'
  );
});

test('options can be unselected individually', function (assert) {
  var options = new Options({
    data: [
      {
        id: 'test',
        text: 'Test'
      },
      {
        id: 'test2',
        text: 'Test2'
      },
      {
        id: 'test3',
        text: 'Test3'
      }
    ]
  });
  var $element = $('<input />');
  $element.val('test,test2,test3');

  var adapter = new InputAdapter($element, options);

  adapter.unselect({
    id: 'test2'
  });

  assert.equal(
    $element.val(),
    'test,test3',
    'The value should contain all the still selected options'
  );
});

test('default values can be set', function (assert) {
  expect(4);

  var options = new Options({
    data: [
      {
        id: 'test',
        text: 'Test'
      }
    ]
  });
  var $element = $('<input value="test" />');

  var adapter = new InputAdapter($element, options);

  adapter.current(function (data) {
    assert.equal(
      data.length,
      1,
      'There should only be a single selected option'
    );

    var item = data[0];

    assert.equal(item.id, 'test');
    assert.equal(item.text, 'Test');
  });

  assert.equal(
    $element.val(),
    'test',
    'The value should not have been altered'
  );
});

test('no default value', function (assert) {
  expect(2);

  var options = new Options({
    data: [
      {
        id: 'test',
        text: 'Test'
      }
    ]
  });
  var $element = $('<input />');

  var adapter = new InputAdapter($element, options);

  adapter.current(function (data) {
    assert.equal(
      data.length,
      0,
      'There should be no selected options'
    );
  });

  assert.equal(
    $element.val(),
    '',
    'The value should not have been altered'
  );
});
