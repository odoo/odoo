module('Dropdown - containerCssClass compatibility');

var $ = require('jquery');
var Utils = require('select2/utils');
var Options = require('select2/options');

var SingleSelection = require('select2/selection/single');
var ContainerCSS = Utils.Decorate(
  SingleSelection,
  require('select2/compat/containerCss')
);

test('all classes will be copied if :all: is used', function (assert) {
  var $element = $('<select class="test copy works"></select>');
  var options = new Options({
    containerCssClass: ':all:'
  });

  var select = new ContainerCSS($element, options);
  var $container = select.render();

  assert.ok($container.hasClass('test'));
  assert.ok($container.hasClass('copy'));
  assert.ok($container.hasClass('works'));
  assert.ok(!$container.hasClass(':all:'));
});

test(':all: can be used with other classes', function (assert) {
  var $element = $('<select class="test copy works"></select>');
  var options = new Options({
    containerCssClass: ':all: other'
  });

  var select = new ContainerCSS($element, options);
  var $container = select.render();

  assert.ok($container.hasClass('test'));
  assert.ok($container.hasClass('copy'));
  assert.ok($container.hasClass('works'));
  assert.ok($container.hasClass('other'));
  assert.ok(!$container.hasClass(':all:'));
});

test('classes can be passed in as a string', function (assert) {
  var $element = $('<select class="test copy works"></select>');
  var options = new Options({
    containerCssClass: 'other'
  });

  var select = new ContainerCSS($element, options);
  var $container = select.render();

  assert.ok($container.hasClass('other'));
});

test('a function can be used based on the element', function (assert){
  var $element = $('<select class="test"></select>');
  var options = new Options({
    containerCssClass: function ($element) {
      return 'function';
    }
  });

  var select = new ContainerCSS($element, options);
  var $container = select.render();

  assert.ok($container.hasClass('function'));
  assert.ok(!$container.hasClass('test'));
});

test(':all: works around custom adapters', function (assert) {
  var $element = $('<select class="test"></select>');
  var options = new Options({
    containerCssClass: ':all: something',
    adaptContainerCssClass: function (clazz) {
      return clazz + '-modified';
    }
  });

  var select = new ContainerCSS($element, options);
  var $container = select.render();

  assert.ok($container.hasClass('something'));

  assert.ok($container.hasClass('test'));
  assert.ok($container.hasClass('test-modified'));
});

module('Selection - adaptContainerCss compatibility');

test('only return when adapted', function (assert) {
  var $element = $('<select class="original"></select>');
  var options = new Options({
    adaptContainerCssClass: function (clazz) {
      return 'modified';
    }
  });

  var select = new ContainerCSS($element, options);
  var $container = select.render();

  assert.ok(!$container.hasClass('original'));
  assert.ok($container.hasClass('modified'));
});
