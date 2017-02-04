module('Data adaptor - Tokenizer');

test('triggers the select event', function (assert) {
  expect(2);

  var SelectData = require('select2/data/select');
  var Tokenizer = require('select2/data/tokenizer');
  var Tags = require('select2/data/tags');

  var Options = require('select2/options');
  var Utils = require('select2/utils');

  var $ = require('jquery');

  var TokenizedSelect = Utils.Decorate(
    Utils.Decorate(SelectData, Tags),
    Tokenizer
  );
  var $select = $('#qunit-fixture .single');

  var options = new Options({
    tags: true,
    tokenSeparators: [',']
  });

  var container = new MockContainer();
  container.dropdown = container.selection = {};
  
  var $container = $('<div></div>');

  var data = new TokenizedSelect($select, options);
  data.bind(container, $container);

  data.on('select', function () {
    assert.ok(true, 'The select event should be triggered');
  });

  data.query({
    term: 'first,second'
  }, function () {
    assert.ok(true, 'The callback should have succeeded');
  });
});

test('createTag can return null', function (assert) {
  expect(3);

  var SelectData = require('select2/data/select');
  var Tokenizer = require('select2/data/tokenizer');
  var Tags = require('select2/data/tags');

  var Options = require('select2/options');
  var Utils = require('select2/utils');

  var $ = require('jquery');

  var TokenizedSelect = Utils.Decorate(
    Utils.Decorate(SelectData, Tags),
    Tokenizer
  );
  var $select = $('#qunit-fixture .single');

  var options = new Options({
    tags: true,
    tokenSeparators: [','],
    createTag: function () {
      assert.ok(true, 'createTag should have been called');

      return null;
    }
  });

  var container = new MockContainer();
  container.dropdown = container.selection = {};

  var $container = $('<div></div>');

  var data = new TokenizedSelect($select, options);
  data.bind(container, $container);

  data.on('select', function (params) {
    if (params.data == null) {
      assert.ok(false, 'Null data should never be selected');
    }
  });

  data.query({
    term: 'first,second'
  }, function () {
    assert.ok(true, 'The callback should have succeeded');
  });
});

test('createTag returning null does not cut the term', function (assert) {
  expect(4);

  var SelectData = require('select2/data/select');
  var Tokenizer = require('select2/data/tokenizer');
  var Tags = require('select2/data/tags');

  var Options = require('select2/options');
  var Utils = require('select2/utils');

  var $ = require('jquery');

  var TokenizedSelect = Utils.Decorate(
    Utils.Decorate(SelectData, Tags),
    Tokenizer
  );
  var $select = $('#qunit-fixture .single');

  var options = new Options({
    tags: true,
    tokenSeparators: [',', '"'],
    createTag: function (params) {
      var term = params.term;

      // Ignore blanks
      if (term.length === 0) {
        return null;
      }

      // Ignore the leading quote
      if (term === '"') {
        return null;
      }

      // If there is a leading quote, check for a second one
      if (term[0] === '"' && term[term.length - 1] !== '"') {
        return null;
      }

      var text = term.substr(1, term.length - 2);

      return {
        id: term,
        text: text
      };
    }
  });

  var container = new MockContainer();
  container.dropdown = container.selection = {};

  var $container = $('<div></div>');

  var data = new TokenizedSelect($select, options);
  data.bind(container, $container);

  data.on('select', function (params) {
    assert.ok(params.data, 'Data should not be null');

    assert.equal(
      params.data.id,
      '"first, second"',
      'The id should have the quotes'
    );

    assert.equal(
      params.data.text,
      'first, second',
      'The text should not have the quotes'
    );
  });

  data.query({
    term: '"first, second",abc'
  }, function () {
    assert.ok(true, 'The callback should have succeeded');
  });
});