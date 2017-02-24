module('Data adapters - Maximum selection length');

var MaximumSelectionLength = require('select2/data/maximumSelectionLength');

var $ = require('jquery');
var Options = require('select2/options');
var Utils = require('select2/utils');

function MaximumSelectionStub () {
  this.called = false;
  this.currentData = [];
}

MaximumSelectionStub.prototype.current = function (callback) {
  callback(this.currentData);
};

MaximumSelectionStub.prototype.val = function (val) {
  this.currentData.push(val);
};

MaximumSelectionStub.prototype.query = function (params, callback) {
  this.called = true;
};

var MaximumSelectionData = Utils.Decorate(
  MaximumSelectionStub,
  MaximumSelectionLength
);

test('0 never displays the notice', function (assert) {
  var zeroOptions = new Options({
    maximumSelectionLength: 0
  });

  var data = new MaximumSelectionData(null, zeroOptions);

  data.trigger = function () {
    assert.ok(false, 'No events should be triggered');
  };

  data.query({
    term: ''
  });

  assert.ok(data.called);

  data = new MaximumSelectionData(null, zeroOptions);

  data.trigger = function () {
    assert.ok(false, 'No events should be triggered');
  };

  data.val('1');

  data.query({
    term: ''
  });

  assert.ok(data.called);

  data = new MaximumSelectionData(null, zeroOptions);

  data.trigger = function () {
    assert.ok(false, 'No events should be triggered');
  };

  data.val('1');
  data.val('2');

  data.query({
    term: ''
  });

  assert.ok(data.called);
});

test('< 0 never displays the notice', function (assert) {
  var negativeOptions = new Options({
    maximumSelectionLength: -1
  });

  var data = new MaximumSelectionData(null, negativeOptions);

  data.trigger = function () {
    assert.ok(false, 'No events should be triggered');
  };

  data.query({
    term: ''
  });

  assert.ok(data.called);

  data = new MaximumSelectionData(null, negativeOptions);

  data.trigger = function () {
    assert.ok(false, 'No events should be triggered');
  };

  data.val('1');

  data.query({
    term: ''
  });

  assert.ok(data.called);

  data = new MaximumSelectionData(null, negativeOptions);

  data.trigger = function () {
    assert.ok(false, 'No events should be triggered');
  };

  data.val('1');
  data.val('2');

  data.query({
    term: ''
  });

  assert.ok(data.called);
});

test('triggers when >= 1 selection' , function (assert) {
  var maxOfOneOptions = new Options({
    maximumSelectionLength: 1
  });
  var data = new MaximumSelectionData(null, maxOfOneOptions);

  data.trigger = function () {
    assert.ok(false, 'No events should be triggered');
  };

  data.query({
    term: ''
  });

  assert.ok(data.called);

  data = new MaximumSelectionData(null, maxOfOneOptions);

  data.trigger = function () {
    assert.ok(true, 'The event should be triggered.');
  };

  data.val('1');

  data.query({
    term: ''
  });

  assert.ok(!data.called);

});

test('triggers when >= 2 selections' , function (assert) {
  var maxOfTwoOptions = new Options({
    maximumSelectionLength: 2
  });
  var data = new MaximumSelectionData(null, maxOfTwoOptions);

  data.trigger = function () {
    assert.ok(false, 'No events should be triggered');
  };

  data.query({
    term: ''
  });

  assert.ok(data.called);

  data = new MaximumSelectionData(null, maxOfTwoOptions);

  data.trigger = function () {
    assert.ok(false, 'No events should be triggered');
  };

  data.val('1');

  data.query({
    term: ''
  });

  assert.ok(data.called);

  data = new MaximumSelectionData(null, maxOfTwoOptions);

  data.trigger = function () {
    assert.ok(true, 'The event should be triggered.');
  };

  data.val('1');
  data.val('2');

  data.query({
    term: ''
  });

  assert.ok(!data.called);

});
