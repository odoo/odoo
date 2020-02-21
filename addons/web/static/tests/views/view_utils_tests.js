odoo.define('web.view_utils_tests', function (require) {
    "use strict";

    var viewUtils = require('web.viewUtils');

    QUnit.module('Views', {}, function () {

    QUnit.module('view_utils');

    QUnit.test('getOptionalFieldsStorageKey (main view)', function (assert) {
        assert.expect(4);

        let key;

        key = viewUtils.getOptionalFieldsStorageKey({
            model: 'partner',
            viewType: 'list',
            fields: ['beer', 'address', 'contact'],
        });
        assert.strictEqual(key, 'optional_fields,partner,list,undefined,address,beer,contact');

        key = viewUtils.getOptionalFieldsStorageKey({
            model: 'user',
            viewType: 'list',
            viewId: undefined,
            fields: ['contact', 'address', 'beer'],
        });
        assert.strictEqual(key, 'optional_fields,user,list,undefined,address,beer,contact');

        key = viewUtils.getOptionalFieldsStorageKey({
            model: 'partner',
            viewType: 'list',
            viewId: 34,
            fields: ['beer', 'contact', 'address'],
        });
        assert.strictEqual(key, 'optional_fields,partner,list,34,address,beer,contact');

        key = viewUtils.getOptionalFieldsStorageKey({
            model: 'partner',
            viewType: 'list',
            viewId: null,
            fields: ['beer', 'contact', 'address'],
        });
        assert.strictEqual(key, 'optional_fields,partner,list,undefined,address,beer,contact');
    });

    QUnit.test('getOptionalFieldsStorageKey (sub view)', function (assert) {
        assert.expect(3);

        let key;

        key = viewUtils.getOptionalFieldsStorageKey({
            model: 'partner',
            viewType: 'form',
            relationalField: 'some_x2m',
            subViewType: 'list',
            fields: ['contact', 'address', 'beer'],
        });
        assert.strictEqual(key, 'optional_fields,partner,form,undefined,some_x2m,list,undefined,address,beer,contact');

        key = viewUtils.getOptionalFieldsStorageKey({
            model: 'partner',
            viewType: 'form',
            viewId: 34,
            relationalField: 'some_x2m',
            subViewType: 'list',
            fields: ['contact', 'address', 'beer'],
        });
        assert.strictEqual(key, 'optional_fields,partner,form,34,some_x2m,list,undefined,address,beer,contact');

        key = viewUtils.getOptionalFieldsStorageKey({
            model: 'partner',
            viewType: 'form',
            viewId: 34,
            relationalField: 'some_x2m',
            subViewType: 'list',
            subViewId: 12,
            fields: ['contact', 'address', 'beer'],
        });
        assert.strictEqual(key, 'optional_fields,partner,form,34,some_x2m,list,12,address,beer,contact');
    });

    });
});
