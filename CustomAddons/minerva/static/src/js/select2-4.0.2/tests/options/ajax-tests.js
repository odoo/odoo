module('Defaults - Ajax');

test('options are merged recursively with default options', function (assert) {
  var defaults = require('select2/defaults');

  var ajaxDelay = 250;
  var ajaxUrl = 'http://www.test.com';

  var mergedOptions;

  defaults.set('ajax--delay', ajaxDelay);

  mergedOptions = defaults.apply({
    ajax: {
      url: ajaxUrl
    }
  });

  assert.equal(
    mergedOptions.ajax.delay,
    ajaxDelay,
    'Ajax default options are present on the merged options'
  );

  assert.equal(
    mergedOptions.ajax.url,
    ajaxUrl,
    'Ajax provided options are present on the merged options'
  );

  defaults.reset();
});