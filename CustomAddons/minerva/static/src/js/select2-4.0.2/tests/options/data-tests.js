module('Options - Attributes');

var $ = require('jquery');

var Options = require('select2/options');

test('no nesting', function (assert) {
  var $test = $('<select data-test="test"></select>');

  var options = new Options({}, $test);

  assert.equal(options.get('test'), 'test');
});

test('with nesting', function (assert) {
  var $test = $('<select data-first--second="test"></select>');

  if ($test[0].dataset == null) {
    assert.ok(
      true,
      'We can not run this test with jQuery 1.x if dataset is not implemented'
    );

    return;
  }

  var options = new Options({}, $test);

  assert.ok(!(options.get('first-Second')));
  assert.equal(options.get('first').second, 'test');
});

test('overrides initialized data', function (assert) {
  var $test = $('<select data-override="yes" data-data="yes"></select>');

  var options = new Options({
    options: 'yes',
    override: 'no'
  }, $test);

  assert.equal(options.get('options'), 'yes');
  assert.equal(options.get('override'), 'yes');
  assert.equal(options.get('data'), 'yes');
});
