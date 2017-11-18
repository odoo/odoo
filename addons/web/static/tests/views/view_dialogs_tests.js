odoo.define('web.view_dialogs_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var dialogs = require('web.view_dialogs');
var Widget = require('web.Widget');

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: 'char'},
                    bar: {string: "Bar", type: "boolean"},
                },
                records: [
                    {id: 1, foo: 'blip', display_name: 'blipblip', bar: true},
                    {id: 2, foo: 'ta tata ta ta', display_name: 'macgyver', bar: false},
                    {id: 3, foo: 'piou piou', display_name: "Jack O'Neill", bar: true},
                ],
            },
        };

    },
}, function () {

    QUnit.module('view_dialogs');

    function createParent(params) {
        var widget = new Widget();

        testUtils.addMockEnvironment(widget, params);
        return widget;
    }

    QUnit.test('formviewdialog buttons in footer are positioned properly', function (assert) {
        assert.expect(2);

        var parent = createParent({
            data: this.data,
            archs: {
                'partner,false,form':
                    '<form string="Partner">' +
                        '<sheet>' +
                            '<group><field name="foo"/></group>' +
                            '<footer><button string="Custom Button" type="object" class="btn-primary"/></footer>' +
                        '</sheet>' +
                    '</form>',
            },
        });

        testUtils.intercept(parent, 'env_updated', function () {
            throw new Error("The environment should not be propagated to the view manager");
        });


        new dialogs.FormViewDialog(parent, {
            res_model: 'partner',
            res_id: 1,
        }).open();

        assert.notOk($('div.modal .modal-body button').length,
            "should not have any button in body");
        assert.strictEqual($('div.modal .modal-footer button').length, 1,
            "should have only one button in footer");
        parent.destroy();
    });

    QUnit.test('SelectCreateDialog use domain, group_by and search default', function (assert) {
        assert.expect(3);

        var search = 0;
        var parent = createParent({
            data: this.data,
            archs: {
                'partner,false,list':
                    '<tree string="Partner">' +
                        '<field name="display_name"/>' +
                        '<field name="foo"/>' +
                    '</tree>',
                'partner,false,search':
                    '<search>' +
                        '<field name="foo" filter_domain="[(\'display_name\',\'ilike\',self), (\'foo\',\'ilike\',self)]"/>' +
                        '<group expand="0" string="Group By">' +
                            '<filter name="groupby_bar" context="{\'group_by\' : \'bar\'}"/>' +
                        '</group>' +
                    '</search>',
            },
            mockRPC: function (route, args) {
                search++;
                if (search === 1 && args.method === 'read_group') {
                    assert.deepEqual(args.kwargs, {
                        context: {group_by: "bar"},
                        domain: [["display_name","like","a"], ["display_name","ilike","piou"], ["foo","ilike","piou"]],
                        fields:["display_name","foo","bar"],
                        groupby:["bar"],
                        orderby: '',
                        lazy: true
                    }, "should search with the complete domain (domain + search), and group by 'bar'");
                }
                if (search === 2 && route === '/web/dataset/search_read') {
                    assert.deepEqual(args, {
                        context: {},
                        domain: [["display_name","like","a"], ["display_name","ilike","piou"], ["foo","ilike","piou"]],
                        fields:["display_name","foo"],
                        model: "partner",
                        limit: 80,
                        sort: ""
                    }, "should search with the complete domain (domain + search)");
                }
                if (search === 3 && route === '/web/dataset/search_read') {
                    assert.deepEqual(args, {
                        context: {},
                        domain: [["display_name","like","a"]],
                        fields:["display_name","foo"],
                        model: "partner",
                        limit: 80,
                        sort: ""
                    }, "should search with the domain");
                }

                return this._super.apply(this, arguments);
            },
        });

        var dialog = new dialogs.SelectCreateDialog(parent, {
            no_create: true,
            readonly: true,
            res_model: 'partner',
            domain: [['display_name', 'like', 'a']],
            context: {
                search_default_groupby_bar: true,
                search_default_foo: 'piou',
            },
        }).open();

        dialog.$('.o_searchview_facet:contains(groupby_bar) .o_facet_remove').click();
        dialog.$('.o_searchview_facet .o_facet_remove').click();

        parent.destroy();
    });

    QUnit.test('SelectCreateDialog correctly evaluates domains', function (assert) {
        assert.expect(1);

        var parent = createParent({
            data: this.data,
            archs: {
                'partner,false,list':
                    '<tree string="Partner">' +
                        '<field name="display_name"/>' +
                        '<field name="foo"/>' +
                    '</tree>',
                'partner,false,search':
                    '<search>' +
                        '<field name="foo"/>' +
                    '</search>',
            },
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.deepEqual(args.domain, [['id', '=', 2]],
                        "should have correctly evaluated the domain");
                }
                return this._super.apply(this, arguments);
            },
            session: {
                user_context: {uid: 2},
            },
        });

        new dialogs.SelectCreateDialog(parent, {
            no_create: true,
            readonly: true,
            res_model: 'partner',
            domain: "[['id', '=', uid]]",
        }).open();

        parent.destroy();
    });

    QUnit.test('SelectCreateDialog list view in readonly', function (assert) {
        assert.expect(1);

        var parent = createParent({
            data: this.data,
            archs: {
                'partner,false,list':
                    '<tree string="Partner" editable="bottom">' +
                        '<field name="display_name"/>' +
                        '<field name="foo"/>' +
                    '</tree>',
                'partner,false,search':
                    '<search/>'
            },
        });

        var dialog = new dialogs.SelectCreateDialog(parent, {
            res_model: 'partner',
        }).open();

        // click on the first row to see if the list is editable
        dialog.$('.o_list_view tbody tr:first td:not(.o_list_record_selector):first').click();

        assert.equal(dialog.$('.o_list_view tbody tr:first td:not(.o_list_record_selector):first input').length, 0,
            "list view should not be editable in a SelectCreateDialog");

        parent.destroy();
    });

});

});
