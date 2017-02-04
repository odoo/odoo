module('Dropdown - selectOnClose');

var $ = require('jquery');

var Utils = require('select2/utils');
var Options = require('select2/options');

var SelectData = require('select2/data/select');

var Results = require('select2/results');
var SelectOnClose = require('select2/dropdown/selectOnClose');

var ModifiedResults = Utils.Decorate(Results, SelectOnClose);

var options = new Options({
  selectOnClose: true
});

test('will not trigger if no results were given', function (assert) {
  expect(0);

  var $element = $('<select></select>');
  var select = new ModifiedResults($element, options, new SelectData($element));

  var $dropdown = select.render();

  var container = new MockContainer();
  select.bind(container, $('<div></div>'));

  select.on('select', function () {
    assert.ok(false, 'The select event should not have been triggered');
  });

  container.trigger('close');
});

test('will not trigger if the results list is empty', function (assert) {
  expect(1);

  var $element = $('<select></select>');
  var select = new ModifiedResults($element, options, new SelectData($element));

  var $dropdown = select.render();

  var container = new MockContainer();
  select.bind(container, $('<div></div>'));

  select.on('select', function () {
    assert.ok(false, 'The select event should not have been triggered');
  });

  select.append({
    results: []
  });

  assert.equal(
    $dropdown.find('li').length,
    0,
    'There should not be any results in the dropdown'
  );

  container.trigger('close');
});

test('will not trigger if no results here highlighted', function (assert) {
  expect(2);

  var $element = $('<select></select>');
  var select = new ModifiedResults($element, options, new SelectData($element));

  var $dropdown = select.render();

  var container = new MockContainer();
  select.bind(container, $('<div></div>'));

  select.on('select', function () {
    assert.ok(false, 'The select event should not have been triggered');
  });

  select.append({
    results: [
      {
        id: '1',
        text: 'Test'
      }
    ]
  });

  assert.equal(
    $dropdown.find('li').length,
    1,
    'There should be one result in the dropdown'
  );

  assert.equal(
    $.trim($dropdown.find('li').text()),
    'Test',
    'The result should be the same as the one we appended'
  );

  container.trigger('close');
});

test('will trigger if there is a highlighted result', function (assert) {
  expect(2);

  var $element = $('<select></select>');
  var select = new ModifiedResults($element, options, new SelectData($element));

  var $dropdown = select.render();

  var container = new MockContainer();
  select.bind(container, $('<div></div>'));

  select.on('select', function () {
    assert.ok(true, 'The select event should have been triggered');
  });

  select.append({
    results: [
      {
        id: '1',
        text: 'Test'
      }
    ]
  });

  assert.equal(
    $dropdown.find('li').length,
    1,
    'There should be one result in the dropdown'
  );

  $dropdown.find('li').addClass('select2-results__option--highlighted');

  container.trigger('close');
});
