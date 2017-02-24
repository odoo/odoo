module('Data adapters - Select - current');

var SelectData = require('select2/data/select');
var $ = require('jquery');
var Options = require('select2/options');
var selectOptions = new Options({});

test('current gets default for single', function (assert) {
  var $select = $('#qunit-fixture .single');

  var data = new SelectData($select, selectOptions);

  data.current(function (data) {
    assert.equal(
      data.length,
      1,
      'There should only be one selected option'
    );

    var option = data[0];

    assert.equal(
      option.id,
      'One',
      'The value of the option tag should be the id'
    );

    assert.equal(
      option.text,
      'One',
      'The text within the option tag should be the text'
    );
  });
});

test('current gets default for multiple', function (assert) {
  var $select = $('#qunit-fixture .multiple');

  var data = new SelectData($select, selectOptions);

  data.current(function (data) {
    assert.equal(
      data.length,
      0,
      'Multiple selects have no default selection.'
    );
  });
});

test('current gets options with explicit value', function (assert) {
  var $select = $('#qunit-fixture .single');

  var $option = $('<option value="1">One</option>');
  $select.append($option);

  var data = new SelectData($select, selectOptions);

  $select.val('1');

  data.current(function (data) {
    assert.equal(
      data.length,
      1,
      'There should be one selected option'
    );

    var option = data[0];

    assert.equal(
      option.id,
      '1',
      'The option value should be the selected id'
    );

    assert.equal(
      option.text,
      'One',
      'The text should match the text for the option tag'
    );
  });
});

test('current gets options with implicit value', function (assert) {
  var $select = $('#qunit-fixture .single');

  var data = new SelectData($select, selectOptions);

  $select.val('One');

  data.current(function (val) {
    assert.equal(
      val.length,
      1,
      'There should only be one selected value'
    );

    var option = val[0];

    assert.equal(
      option.id,
      'One',
      'The id should be the same as the option text'
    );

    assert.equal(
      option.text,
      'One',
      'The text should be the same as the option text'
    );
  });
});

test('select works for single', function (assert) {
  var $select = $('#qunit-fixture .single-with-placeholder');

  var data = new SelectData($select, selectOptions);

  assert.equal($select.val(), 'placeholder');

  data.select({
    id: 'One',
    text: 'One'
  });

  assert.equal($select.val(), 'One');
});

test('multiple sets the value', function (assert) {
  var $select = $('#qunit-fixture .multiple');

  var data = new SelectData($select, selectOptions);

  assert.equal($select.val(), null);

  data.select({
    id: 'Two',
    text: 'Two'
  });

  assert.deepEqual($select.val(), ['Two']);
});

test('multiple adds to the old value', function (assert) {
  var $select = $('#qunit-fixture .multiple');

  var data = new SelectData($select, selectOptions);

  $select.val(['Two']);

  assert.deepEqual($select.val(), ['Two']);

  data.select({
    id: 'One',
    text: 'One'
  });

  assert.deepEqual($select.val(), ['One', 'Two']);
});

test('duplicates - single - same id on select triggers change',
  function (assert) {
  var $select = $('#qunit-fixture .duplicates');

  var data = new SelectData($select, data);
  var second = $('#qunit-fixture .duplicates option')[2];

  var changeTriggered = false;

  assert.equal($select.val(), 'one');

  $select.on('change', function () {
    changeTriggered = true;
  });

  data.select({
    id: 'one',
    text: 'Uno',
    element: second
  });

  assert.equal(
    $select.val(),
    'one',
    'The value never changed'
  );

  assert.ok(
    changeTriggered,
    'The change event should be triggered'
  );

  assert.ok(
    second.selected,
    'The second duplicate is selected, not the first'
  );
});

test('duplicates - single - different id on select triggers change',
  function (assert) {
  var $select = $('#qunit-fixture .duplicates');

  var data = new SelectData($select, data);
  var second = $('#qunit-fixture .duplicates option')[2];

  var changeTriggered = false;

  $select.val('two');

  $select.on('change', function () {
    changeTriggered = true;
  });

  data.select({
    id: 'one',
    text: 'Uno',
    element: second
  });

  assert.equal(
    $select.val(),
    'one',
    'The value changed to the duplicate id'
  );

  assert.ok(
    changeTriggered,
    'The change event should be triggered'
  );

  assert.ok(
    second.selected,
    'The second duplicate is selected, not the first'
  );
});

test('duplicates - multiple - same id on select triggers change',
function (assert) {
  var $select = $('#qunit-fixture .duplicates-multi');

  var data = new SelectData($select, data);
  var second = $('#qunit-fixture .duplicates-multi option')[2];

  var changeTriggered = false;

  $select.val(['one']);

  $select.on('change', function () {
    changeTriggered = true;
  });

  data.select({
    id: 'one',
    text: 'Uno',
    element: second
  });

  assert.deepEqual(
    $select.val(),
    ['one', 'one'],
    'The value now has duplicates'
  );

  assert.ok(
    changeTriggered,
    'The change event should be triggered'
  );

  assert.ok(
    second.selected,
    'The second duplicate is selected, not the first'
  );
});

test('duplicates - multiple - different id on select triggers change',
function (assert) {
  var $select = $('#qunit-fixture .duplicates-multi');

  var data = new SelectData($select, data);
  var second = $('#qunit-fixture .duplicates-multi option')[2];

  var changeTriggered = false;

  $select.val(['two']);

  $select.on('change', function () {
    changeTriggered = true;
  });

  data.select({
    id: 'one',
    text: 'Uno',
    element: second
  });

  assert.deepEqual(
    $select.val(),
    ['two', 'one'],
    'The value has the new id'
  );

  assert.ok(
    changeTriggered,
    'The change event should be triggered'
  );

  assert.ok(
    second.selected,
    'The second duplicate is selected, not the first'
  );
});

module('Data adapter - Select - query');

test('all options are returned with no term', function (assert) {
  var $select = $('#qunit-fixture .single');

  var data = new SelectData($select, selectOptions);

  data.query({}, function (data) {
    assert.equal(
      data.results.length,
      1,
      'The number of items returned should be equal to the number of options'
    );
  });
});

test('the matcher checks the text', function (assert) {
  var $select = $('#qunit-fixture .single');

  var data = new SelectData($select, selectOptions);

  data.query({
    term: 'One'
  }, function (data) {
    assert.equal(
      data.results.length,
      1,
      'Only the "One" option should be found'
    );
  });
});

test('the matcher ignores case', function (assert) {
  var $select = $('#qunit-fixture .single');

  var data = new SelectData($select, selectOptions);

  data.query({
    term: 'one'
  }, function (data) {
    assert.equal(
      data.results.length,
      1,
      'The "One" option should still be found'
    );
  });
});

test('no options may be returned with no matches', function (assert) {
  var $select = $('#qunit-fixture .single');

  var data = new SelectData($select, selectOptions);

  data.query({
    term: 'qwerty'
  }, function (data) {
    assert.equal(
      data.results.length,
      0,
      'Only matching items should be returned'
    );
  });
});

test('optgroup tags are marked with children', function (assert) {
  var $select = $('#qunit-fixture .groups');

  var data = new SelectData($select, selectOptions);

  data.query({}, function (data) {
    assert.ok(
      'children' in data.results[0],
      'The optgroup element should have children when queried'
    );
  });
});

test('empty optgroups are still shown when queried', function (assert) {
  var $select = $('#qunit-fixture .groups');

  var data = new SelectData($select, selectOptions);

  data.query({}, function (data) {
    assert.equal(
      data.results.length,
      2,
      'The empty optgroup element should still be returned when queried'
    );

    var item = data.results[1];

    assert.equal(
      item.text,
      'Empty',
      'The text of the empty optgroup should match the label'
    );

    assert.equal(
      item.children.length,
      0,
      'There should be no children in the empty opgroup'
    );
  });
});

test('multiple options with the same value are returned', function (assert) {
  var $select = $('#qunit-fixture .duplicates');

  var data = new SelectData($select, selectOptions);

  data.query({}, function (data) {
    assert.equal(
      data.results.length,
      3,
      'The duplicate option should still be returned when queried'
    );

    var first = data.results[0];
    var duplicate = data.results[2];

    assert.equal(
      first.id,
      duplicate.id,
      'The duplicates should have the same id'
    );

    assert.notEqual(
      first.text,
      duplicate.text,
      'The duplicates do not have the same text'
    );
  });
});

test('data objects use the text of the option', function (assert) {
  var $select = $('#qunit-fixture .duplicates');

  var data = new SelectData($select, selectOptions);

  var $option = $('<option>&amp;</option>');

  var item = data.item($option);

  assert.equal(item.id, '&');
  assert.equal(item.text, '&');
});
