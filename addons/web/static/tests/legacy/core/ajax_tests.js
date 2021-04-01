odoo.define('web.ajax_tests', function (require) {
"use strict";

var ajax = require('web.ajax');

QUnit.module('core', function () {

    var test_css_url = '/test_assetsbundle/static/src/css/test_cssfile1.css';
    var test_link_selector = 'link[href="' + test_css_url + '"]';

    QUnit.module('ajax', {
        beforeEach: function () {
            $(test_link_selector).remove();
        },
        afterEach: function () {
            $(test_link_selector).remove();
        }
    });

    QUnit.test('loadCSS', function (assert) {
        var done = assert.async();
        assert.expect(2);
        ajax.loadCSS(test_css_url).then(function () {
            var $links = $(test_link_selector);
            assert.strictEqual($links.length, 1, "The css should be added to the dom.");
            ajax.loadCSS(test_css_url).then(function () {
                var $links = $(test_link_selector);
                assert.strictEqual($links.length, 1, "The css should have been added only once.");
                done();
            });
        });
    });
});

});
