module('Options - Deprecated - initSelection');

var $ = require('jquery');
var Options = require('select2/options');

test('converted into dataAdapter.current', function (assert) {
  expect(5);

  var $test = $('<select></select>');
  var called = false;

  var options = new Options({
    initSelection: function ($element, callback) {
      called = true;

      callback([{
        id: '1',
        text: '2'
      }]);
    }
  }, $test);

  assert.ok(!called, 'initSelection should not have been called');

  var DataAdapter = options.get('dataAdapter');
  var data = new DataAdapter($test, options);

  data.current(function (data) {
    assert.equal(
      data.length,
      1,
      'There should have only been one object selected'
    );

    var item = data[0];

    assert.equal(
      item.id,
      '1',
      'The id should have been set by initSelection'
    );

    assert.equal(
      item.text,
      '2',
      'The text should have been set by initSelection'
    );
  });

  assert.ok(called, 'initSelection should have been called');
});

test('single option converted to array automatically', function (assert) {
  expect(2);

  var $test = $('<select></select>');
  var called = false;

  var options = new Options({
    initSelection: function ($element, callback) {
      called = true;

      callback({
        id: '1',
        text: '2'
      });
    }
  }, $test);

  var DataAdapter = options.get('dataAdapter');
  var data = new DataAdapter($test, options);

  data.current(function (data) {
    assert.ok(
      $.isArray(data),
      'The data should have been converted to an array'
    );
  });

  assert.ok(called, 'initSelection should have been called');
});

test('only called once', function (assert) {
  expect(8);

  var $test = $('<select><option value="3" selected>4</option></select>');
  var called = 0;

  var options = new Options({
    initSelection: function ($element, callback) {
      called++;

      callback([{
        id: '1',
        text: '2'
      }]);
    }
  }, $test);

  var DataAdapter = options.get('dataAdapter');
  var data = new DataAdapter($test, options);

  data.current(function (data) {
    assert.equal(
      data.length,
      1,
      'There should have only been a single option'
    );

    var item = data[0];

    assert.equal(
      item.id,
      '1',
      'The id should match the one given by initSelection'
    );

    assert.equal(
      item.text,
      '2',
      'The text should match the one given by initSelection'
    );
  });

  assert.equal(
    called,
    1,
    'initSelection should have been called'
  );

  data.current(function (data) {
    assert.equal(
      data.length,
      1,
      'There should have only been a single option'
    );

    var item = data[0];

    assert.equal(
      item.id,
      '3',
      'The id should match the value given in the DOM'
    );

    assert.equal(
      item.text,
      '4',
      'The text should match the text given in the DOM'
    );
  });

  assert.equal(
    called,
    1,
    'initSelection should have only been called once'
  );
});

module('Options - Deprecated - query');

test('converted into dataAdapter.query automatically', function (assert) {
  expect(6);

  var $test = $('<select></select>');
  var called = false;

  var options = new Options({
    query: function (params) {
      called = true;

      params.callback({
        results: [
          {
            id: 'test',
            text: params.term
          }
        ]
      });
    }
  }, $test);

  assert.ok(!called, 'The query option should not have been called');

  var DataAdapter = options.get('dataAdapter');
  var data = new DataAdapter($test, options);

  data.query({
    term: 'term'
  }, function (data) {
    assert.ok(
      'results' in data,
      'It should have included the results key'
    );

    assert.equal(
      data.results.length,
      1,
      'There should have only been a single result returned'
    );

    var item = data.results[0];

    assert.equal(
      item.id,
      'test',
      'The id should have been returned from the query function'
    );

    assert.equal(
      item.text,
      'term',
      'The text should have matched the term that was passed in'
    );
  });

  assert.ok(called, 'The query function should have been called');
});

module('Options - deprecated - data-ajax-url');

test('converted ajax-url to ajax--url automatically', function (assert) {
  var $test = $('<select data-ajax-url="test://url"></select>');
  var options = new Options({}, $test);

  assert.ok(
    options.get('ajax'),
    'The `ajax` key was automatically created'
  );
  assert.equal(
    options.get('ajax').url,
    'test://url',
    'The `url` property for the `ajax` option was filled in correctly'
  );
});

test('converted select2-tags to data/tags automatically', function (assert) {
  var $test = $('<select data-select2-tags="original data"></select>');
  var options = new Options({}, $test);

  assert.ok(
    options.get('tags'),
    'The `tags` key is automatically set to true'
  );
  assert.equal(
    options.get('data'),
    'original data',
    'The `data` key is created with the original data'
  );
});
