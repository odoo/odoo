odoo.define('web.base_import_mobile_tests', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Base Import Mobile Tests', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                },
            },
        };
    }
});

QUnit.test('import button should be hidden in list on mobile screens', async function (assert) {
    assert.expect(1);

    var list = await createView({
        View: ListView,
        model: 'foo',
        data: this.data,
        arch: '<tree><field name="foo"/></tree>',
    });

    assert.notOk(list.$buttons.find('.o_button_import').is(':visible'),
        "import button should be hidden");
    list.destroy();
});

QUnit.test('import button should be hidden in kanban on mobile screens', async function (assert) {
    assert.expect(1);

    var kanban = await createView({
        View: KanbanView,
        model: 'foo',
        data: this.data,
        arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                    '<field name="foo"/>' +
                    '</div>' +
                '</t></templates></kanban>',
    });

    assert.notOk(kanban.$buttons.find('.o_button_import').is(':visible'),
        "import button should be hidden");
    kanban.destroy();
});

});
