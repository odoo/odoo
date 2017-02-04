module('Selection containers - Placeholders - Allow clear');

var Placeholder = require('select2/selection/placeholder');
var AllowClear = require('select2/selection/allowClear');

var SingleSelection = require('select2/selection/single');

var $ = require('jquery');
var Options = require('select2/options');
var Utils = require('select2/utils');

var AllowClearPlaceholder = Utils.Decorate(
  Utils.Decorate(SingleSelection, Placeholder),
  AllowClear
);

var allowClearOptions = new Options({
  placeholder: {
    id: 'placeholder',
    text: 'This is the placeholder'
  },
  allowClear: true
});

test('clear is not displayed for single placeholder', function (assert) {
  var selection = new AllowClearPlaceholder(
    $('#qunit-fixture .single-with-placeholder'),
    allowClearOptions
  );

  var $selection = selection.render();

  selection.update([{
    id: 'placeholder'
  }]);

  assert.equal(
    $selection.find('.select2-selection__clear').length,
    0,
    'The clear icon should not be displayed'
  );
});

test('clear is not displayed for multiple placeholder', function (assert) {
  var selection = new AllowClearPlaceholder(
    $('#qunit-fixture .single-with-placeholder'),
    allowClearOptions
  );

  var $selection = selection.render();

  selection.update([]);

  assert.equal(
    $selection.find('.select2-selection__clear').length,
    0,
    'The clear icon should not be displayed'
  );
});


test('clear is displayed for placeholder', function (assert) {
  var selection = new AllowClearPlaceholder(
    $('#qunit-fixture .single-with-placeholder'),
    allowClearOptions
  );

  var $selection = selection.render();

  selection.update([{
    id: 'one',
    test: 'one'
  }]);

  assert.equal(
    $selection.find('.select2-selection__clear').length,
    1,
    'The clear icon should be displayed'
  );
});

test('clicking clear will set the placeholder value', function (assert) {
  var $element = $('#qunit-fixture .single-with-placeholder');

  var selection = new AllowClearPlaceholder(
    $element,
    allowClearOptions
  );
  var container = new MockContainer();

  var $selection = selection.render();

  selection.bind(container, $('<div></div'));

  $element.val('One');
  selection.update([{
    id: 'One',
    text: 'One'
  }]);

  var $remove = $selection.find('.select2-selection__clear');
  $remove.trigger('mousedown');

  assert.equal(
    $element.val(),
    'placeholder',
    'The value should have been reset to the placeholder'
  );
});

test('clicking clear will trigger the unselect event', function (assert) {
  expect(3);

  var $element = $('#qunit-fixture .single-with-placeholder');

  var selection = new AllowClearPlaceholder(
    $element,
    allowClearOptions
  );
  var container = new MockContainer();

  var $selection = selection.render();

  selection.bind(container, $('<div></div'));

  $element.val('One');
  selection.update([{
    id: 'One',
    text: 'One'
  }]);

  selection.on('unselect', function (ev) {
    assert.ok(
      'data' in ev && ev.data,
      'The event should have been triggered with the data property'
    );

    assert.ok(
      $.isPlainObject(ev.data),
      'The data should be an object'
    );

    assert.equal(
      ev.data.id,
      'One',
      'The previous object should be unselected'
    );
  });

  var $remove = $selection.find('.select2-selection__clear');
  $remove.trigger('mousedown');
});



test('preventing the unselect event cancels the clearing', function (assert) {
  var $element = $('#qunit-fixture .single-with-placeholder');

  var selection = new AllowClearPlaceholder(
    $element,
    allowClearOptions
  );
  var container = new MockContainer();

  var $selection = selection.render();

  selection.bind(container, $('<div></div'));

  $element.val('One');
  selection.update([{
    id: 'One',
    text: 'One'
  }]);

  selection.on('unselect', function (ev) {
    ev.prevented = true;
  });

  var $remove = $selection.find('.select2-selection__clear');
  $remove.trigger('mousedown');

  assert.equal(
    $element.val(),
    'One',
    'The placeholder should not have been set'
  );
});

test('clear does not work when disabled', function (assert) {
  var $element = $('#qunit-fixture .single-with-placeholder');

  var selection = new AllowClearPlaceholder(
    $element,
    allowClearOptions
  );
  var container = new MockContainer();

  var $selection = selection.render();

  selection.bind(container, $('<div></div'));

  selection.update([{
    id: 'One',
    text: 'One'
  }]);

  $element.val('One');
  selection.options.set('disabled', true);

  var $remove = $selection.find('.select2-selection__clear');
  $remove.trigger('mousedown');

  assert.equal(
    $element.val(),
    'One',
    'The placeholder should not have been set'
  );
});
