odoo.define('account.no_content_help_widget_tests', function (require) {
"use strict";

var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('account', {
    beforeEach: function () {
        this.data = {
            'account.invoice': {
                fields: {
                    foo: {string: "Foo", type: "char"},
                },
                records: []
            },
        };
    }
}, function () {
    QUnit.module('no content help');
    QUnit.test('no content helper when no data with always reload help context', function (assert) {
       assert.expect(1);

       var list = createView({
           View: ListView,
           model: 'account.invoice',
           data: this.data,
           arch: '<tree><field name="foo"/></tree>',
           viewOptions: {
               action: {
                   help: '<p class="hello">click to add a partner</p>'
               }
           },
           mockRPC: function (route, args) {
               if (args.method === 'get_empty_list_help') {
                   assert.ok(true, "should call get_empty_list_help method");
                   return $.when();
               }
               return this._super.apply(this, arguments);
           },
       });
       list.destroy();
});

});
});
