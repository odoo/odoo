odoo.define('lunch.lunchKanbanTests', function (require) {
"use strict";

const LunchKanbanView = require('lunch.LunchKanbanView');

const testUtils = require('web.test_utils');
const {createLunchKanbanView, mockLunchRPC} = require('lunch.test_utils');

QUnit.module('Views');

QUnit.module('LunchKanbanView', {
    beforeEach() {
        const PORTAL_GROUP_ID = 1234;

        this.data = {
            'product': {
                fields: {
                    is_available_at: {string: 'Product Availability', type: 'many2one', relation: 'lunch.location'},
                    category_id: {string: 'Product Category', type: 'many2one', relation: 'lunch.product.category'},
                    supplier_id: {string: 'Vendor', type: 'many2one', relation: 'lunch.supplier'},
                },
                records: [
                    {id: 1, name: 'Tuna sandwich', is_available_at: 1},
                ],
            },
            'lunch.order': {
                fields: {},
                update_quantity() {
                    return Promise.resolve();
                },
            },
            'lunch.product.category': {
                fields: {},
                records: [],
            },
            'lunch.supplier': {
                fields: {},
                records: [],
            },
            'ir.model.data': {
                fields: {},
                xmlid_to_res_id() {
                    return Promise.resolve(PORTAL_GROUP_ID);
                },
            },
            'lunch.location': {
                fields: {
                    name: {string: 'Name', type: 'char'},
                },
                records: [
                    {id: 1, name: "Office 1"},
                    {id: 2, name: "Office 2"},
                ],
            },
            'res.users': {
                fields: {
                    name: {string: 'Name', type: 'char'},
                    groups_id: {string: 'Groups', type: 'many2many'},
                },
                records: [
                    {id: 1, name: "Mitchell Admin", groups_id: []},
                    {id: 2, name: "Marc Demo", groups_id: []},
                    {id: 3, name: "Jean-Luc Portal", groups_id: [PORTAL_GROUP_ID]},
                ],
            },
        };
        this.regularInfos = {
            username: "Marc Demo",
            wallet: 36.5,
            is_manager: false,
            currency: {
                symbol: "\u20ac",
                position: "after"
            },
            user_location: [2, "Office 2"],
        };
        this.managerInfos = {
            username: "Mitchell Admin",
            wallet: 47.6,
            is_manager: true,
            currency: {
                symbol: "\u20ac",
                position: "after"
            },
            user_location: [2, "Office 2"],
        };
    },
}, function () {
    QUnit.test('basic rendering', async function (assert) {
        assert.expect(7);

        const kanban = await createLunchKanbanView({
            View: LunchKanbanView,
            model: 'product',
            data: this.data,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="name"/></div>
                        </t>
                    </templates>
                </kanban>
            `,
            mockRPC: mockLunchRPC({
                infos: this.regularInfos,
                userLocation: this.data['lunch.location'].records[0].id,
            }),
        });

        assert.containsOnce(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)',
            "should have 1 records in the renderer");

        // check view layout
        assert.containsN(kanban, '.o_content > div', 2,
            "should have 2 columns");
        assert.containsOnce(kanban, '.o_content > div.o_search_panel',
            "should have a 'lunch filters' column");
        assert.containsOnce(kanban, '.o_content > .o_lunch_kanban',
            "should have a 'kanban lunch wrapper' column");
        assert.containsOnce(kanban, '.o_lunch_kanban > .o_kanban_view',
            "should have a 'classical kanban view' column");
        assert.hasClass(kanban.$('.o_kanban_view'), 'o_lunch_kanban_view',
            "should have classname 'o_lunch_kanban_view'");
        assert.containsOnce(kanban, '.o_lunch_kanban > span > .o_lunch_kanban_banner',
            "should have a 'lunch kanban' banner");

        kanban.destroy();
    });

    QUnit.test('no flickering at reload', async function (assert) {
        assert.expect(2);

        const self = this;
        let infosProm = Promise.resolve();
        const kanban = await createLunchKanbanView({
            View: LunchKanbanView,
            model: 'product',
            data: this.data,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="name"/></div>
                        </t>
                    </templates>
                </kanban>
            `,
            mockRPC: function (route, args) {
                if (route === '/lunch/user_location_get') {
                    return Promise.resolve(self.data['lunch.location'].records[0].id);
                }
                if (route === '/lunch/infos') {
                    return Promise.resolve(self.regularInfos);
                }
                var result = this._super.apply(this, arguments);
                if (args.method === 'xmlid_to_res_id') {
                    // delay the rendering of the lunch widget
                    return infosProm.then(_.constant(result));
                }
                return result;
            },
        });

        infosProm = testUtils.makeTestPromise();
        kanban.reload();

        assert.strictEqual(kanban.$('.o_lunch_widget').length, 1,
            "old widget should still be present");

        await infosProm.resolve();

        assert.strictEqual(kanban.$('.o_lunch_widget').length, 1);

        kanban.destroy();
    });

    QUnit.module('LunchKanbanWidget', function () {

        QUnit.test('empty cart', async function (assert) {
            assert.expect(3);

            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: mockLunchRPC({
                    infos: this.regularInfos,
                    userLocation: this.data['lunch.location'].records[0].id,
                }),
            });

            const $kanbanWidget = kanban.$('.o_lunch_widget');

            assert.containsN($kanbanWidget, '> .o_lunch_widget_info', 3,
                "should have 3 columns");
            assert.isVisible($kanbanWidget.find('> .o_lunch_widget_info:first'),
                "should have the first column visible");
            assert.strictEqual($kanbanWidget.find('> .o_lunch_widget_info:not(:first)').html().trim(), "",
                "all columns but the first should be empty");

            kanban.destroy();
        });

        QUnit.test('search panel domain location', async function (assert) {
            assert.expect(10);
            const locationId = this.data['lunch.location'].records[0].id;
            const regularInfos = _.extend({}, this.regularInfos);

            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: function (route, args) {
                    assert.step(route);

                    if (route.startsWith('/lunch')) {
                        return mockLunchRPC({
                            infos: regularInfos,
                            userLocation: locationId,
                        }).apply(this, arguments);
                    }
                    if (args.method === 'search_panel_select_multi_range') {
                        assert.deepEqual(args.kwargs.search_domain, [["is_available_at", "in", [locationId]]],
                            'The initial domain of the search panel must contain the user location');
                    }
                    if (route === '/web/dataset/search_read') {
                        assert.deepEqual(args.domain, [["is_available_at", "in", [locationId]]],
                            'The domain for fetching actual data should be correct');
                    }
                    return this._super.apply(this, arguments);
                }
            });
            assert.verifySteps([
                '/lunch/user_location_get',
                '/web/dataset/call_kw/product/search_panel_select_multi_range',
                '/web/dataset/call_kw/product/search_panel_select_multi_range',
                '/web/dataset/search_read',
                '/lunch/infos',
                '/web/dataset/call_kw/ir.model.data/xmlid_to_res_id',
            ])

            kanban.destroy();
        });

        QUnit.test('search panel domain location false: fetch products in all locations', async function (assert) {
            assert.expect(10);
            const regularInfos = _.extend({}, this.regularInfos);

            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: function (route, args) {
                    assert.step(route);

                    if (route.startsWith('/lunch')) {
                        return mockLunchRPC({
                            infos: regularInfos,
                            userLocation: false,
                        }).apply(this, arguments);
                    }
                    if (args.method === 'search_panel_select_multi_range') {
                        assert.deepEqual(args.kwargs.search_domain, [],
                            'The domain should not exist since the location is false.');
                    }
                    if (route === '/web/dataset/search_read') {
                        assert.deepEqual(args.domain, [],
                            'The domain for fetching actual data should be correct');
                    }
                    return this._super.apply(this, arguments);
                }
            });
            assert.verifySteps([
                '/lunch/user_location_get',
                '/web/dataset/call_kw/product/search_panel_select_multi_range',
                '/web/dataset/call_kw/product/search_panel_select_multi_range',
                '/web/dataset/search_read',
                '/lunch/infos',
                '/web/dataset/call_kw/ir.model.data/xmlid_to_res_id',
            ])

            kanban.destroy();
        });

        QUnit.test('non-empty cart', async function (assert) {
            assert.expect(17);

            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: mockLunchRPC({
                    infos: Object.assign({}, this.regularInfos, {
                        total: "3.00",
                        lines: [
                            {
                                product: [1, "Tuna sandwich", "3.00"],
                                toppings: [],
                                quantity: 1.0,
                            },
                        ],
                    }),
                    userLocation: this.data['lunch.location'].records[0].id,
                }),
            });

            const $kanbanWidget = kanban.$('.o_lunch_widget');

            assert.containsN($kanbanWidget, '> .o_lunch_widget_info', 3,
                "should have 3 columns");

            assert.containsOnce($kanbanWidget, '.o_lunch_widget_info:eq(1)',
                "should have a second column");

            const $widgetSecondColumn = $kanbanWidget.find('.o_lunch_widget_info:eq(1)');

            assert.containsOnce($widgetSecondColumn, '.o_lunch_widget_unlink',
                "should have a button to clear the order");

            assert.containsOnce($widgetSecondColumn, '.o_lunch_widget_lines > li',
                "should have 1 order line");

            const $firstLine = $widgetSecondColumn.find('.o_lunch_widget_lines > li:first');
            assert.containsOnce($firstLine, 'button.o_remove_product',
                "should have a button to remove a product quantity on each line");
            assert.containsOnce($firstLine, 'button.o_add_product',
                "should have a button to add a product quantity on each line");
            assert.containsOnce($firstLine, '.o_lunch_product_quantity > :eq(1)',
                "should have the line's quantity");
            assert.strictEqual($firstLine.find('.o_lunch_product_quantity > :eq(1)').text().trim(), "1",
                "should have 1 as the line's quantity");
            assert.containsOnce($firstLine, '.o_lunch_open_wizard',
                "should have the line's product name to open the wizard");
            assert.strictEqual($firstLine.find('.o_lunch_open_wizard').text().trim(), "Tuna sandwich",
                "should have 'Tuna sandwich' as the line's product name");
            assert.containsOnce($firstLine, '.o_field_monetary',
                "should have the line's amount");
            assert.strictEqual($firstLine.find('.o_field_monetary').text().trim(), "3.00€",
                "should have '3.00€' as the line's amount");

            assert.containsOnce($kanbanWidget, '.o_lunch_widget_info:eq(2)',
                "should have a third column");

            const $widgetThirdColumn = kanban.$('.o_lunch_widget .o_lunch_widget_info:eq(2)');

            assert.containsOnce($widgetThirdColumn, '.o_field_monetary',
                "should have an account balance");
            assert.strictEqual($widgetThirdColumn.find('.o_field_monetary').text().trim(), "3.00€",
                "should have '3.00€' in the account balance");
            assert.containsOnce($widgetThirdColumn, '.o_lunch_widget_order_button',
                "should have a button to validate the order");
            assert.strictEqual($widgetThirdColumn.find('.o_lunch_widget_order_button').text().trim(), "Order now",
                "should have 'Order now' as the validate order button text");

            kanban.destroy();
        });

        QUnit.test('ordered cart', async function (assert) {
            assert.expect(15);

            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: mockLunchRPC({
                    infos: Object.assign({}, this.regularInfos, {
                        raw_state: "ordered",
                        state: "Ordered",
                        lines: [
                            {
                                product: [1, "Tuna sandwich", "3.00"],
                                toppings: [],
                                quantity: 1.0,
                            },
                        ],
                    }),
                    userLocation: this.data['lunch.location'].records[0].id,
                }),
            });

            const $kanbanWidget = kanban.$('.o_lunch_widget');

            assert.containsN($kanbanWidget, '> .o_lunch_widget_info', 3,
                "should have 3 columns");

            assert.containsOnce($kanbanWidget, '.o_lunch_widget_info:eq(1)',
                "should have a second column");

            const $widgetSecondColumn = $kanbanWidget.find('.o_lunch_widget_info:eq(1)');

            assert.containsOnce($widgetSecondColumn, '.o_lunch_widget_unlink',
                "should have a button to clear the order");
            assert.containsOnce($widgetSecondColumn, '.badge.badge-warning.o_lunch_ordered',
                "should have an ordered state badge");
            assert.strictEqual($widgetSecondColumn.find('.o_lunch_ordered').text().trim(), "Ordered",
                "should have 'Ordered' in the state badge");

            assert.containsOnce($widgetSecondColumn, '.o_lunch_widget_lines > li',
                "should have 1 order line");

            const $firstLine = $widgetSecondColumn.find('.o_lunch_widget_lines > li:first');
            assert.containsOnce($firstLine, 'button.o_remove_product',
                "should have a button to remove a product quantity on each line");
            assert.containsOnce($firstLine, 'button.o_add_product',
                "should have a button to add a product quantity on each line");
            assert.containsOnce($firstLine, '.o_lunch_product_quantity > :eq(1)',
                "should have the line's quantity");
            assert.strictEqual($firstLine.find('.o_lunch_product_quantity > :eq(1)').text().trim(), "1",
                "should have 1 as the line's quantity");
            assert.containsOnce($firstLine, '.o_lunch_open_wizard',
                "should have the line's product name to open the wizard");
            assert.strictEqual($firstLine.find('.o_lunch_open_wizard').text().trim(), "Tuna sandwich",
                "should have 'Tuna sandwich' as the line's product name");
            assert.containsOnce($firstLine, '.o_field_monetary',
                "should have the line's amount");
            assert.strictEqual($firstLine.find('.o_field_monetary').text().trim(), "3.00€",
                "should have '3.00€' as the line's amount");

            assert.strictEqual($kanbanWidget.find('> .o_lunch_widget_info:eq(2)').html().trim(), "",
                "third column should be empty");

            kanban.destroy();
        });

        QUnit.test('confirmed cart', async function (assert) {
            assert.expect(15);

            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: mockLunchRPC({
                    infos: Object.assign({}, this.regularInfos, {
                        raw_state: "confirmed",
                        state: "Received",
                        lines: [
                            {
                                product: [1, "Tuna sandwich", "3.00"],
                                toppings: [],
                                quantity: 1.0,
                            },
                        ],
                    }),
                    userLocation: this.data['lunch.location'].records[0].id,
                }),
            });

            const $kanbanWidget = kanban.$('.o_lunch_widget');

            assert.containsN($kanbanWidget, '> .o_lunch_widget_info', 3,
                "should have 3 columns");

            assert.containsOnce($kanbanWidget, '.o_lunch_widget_info:eq(1)',
                "should have a second column");

            const $widgetSecondColumn = $kanbanWidget.find('.o_lunch_widget_info:eq(1)');

            assert.containsNone($widgetSecondColumn, '.o_lunch_widget_unlink',
                "shouldn't have a button to clear the order");
            assert.containsOnce($widgetSecondColumn, '.badge.badge-success.o_lunch_confirmed',
                "should have a confirmed state badge");
            assert.strictEqual($widgetSecondColumn.find('.o_lunch_confirmed').text().trim(), "Received",
                "should have 'Received' in the state badge");

            assert.containsOnce($widgetSecondColumn, '.o_lunch_widget_lines > li',
                "should have 1 order line");

            const $firstLine = $widgetSecondColumn.find('.o_lunch_widget_lines > li:first');
            assert.containsNone($firstLine, 'button.o_remove_product',
                "shouldn't have a button to remove a product quantity on each line");
            assert.containsNone($firstLine, 'button.o_add_product',
                "shouldn't have a button to add a product quantity on each line");
            assert.containsOnce($firstLine, '.o_lunch_product_quantity',
                "should have the line's quantity");
            assert.strictEqual($firstLine.find('.o_lunch_product_quantity').text().trim(), "1",
                "should have 1 as the line's quantity");
            assert.containsOnce($firstLine, '.o_lunch_open_wizard',
                "should have the line's product name to open the wizard");
            assert.strictEqual($firstLine.find('.o_lunch_open_wizard').text().trim(), "Tuna sandwich",
                "should have 'Tuna sandwich' as the line's product name");
            assert.containsOnce($firstLine, '.o_field_monetary',
                "should have the line's amount");
            assert.strictEqual($firstLine.find('.o_field_monetary').text().trim(), "3.00€",
                "should have '3.00€' as the line's amount");

            assert.strictEqual($kanbanWidget.find('> .o_lunch_widget_info:eq(2)').html().trim(), "",
                "third column should be empty");

            kanban.destroy();
        });

        QUnit.test('regular user', async function (assert) {
            assert.expect(11);

            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: mockLunchRPC({
                    infos: this.regularInfos,
                    userLocation: this.data['lunch.location'].records[0].id,
                }),
            });

            const $kanbanWidget = kanban.$('.o_lunch_widget');

            assert.containsOnce($kanbanWidget, '.o_lunch_widget_info:first',
                "should have a first column");

            const $widgetFirstColumn = $kanbanWidget.find('.o_lunch_widget_info:first');

            assert.containsOnce($widgetFirstColumn, 'img.rounded-circle',
                "should have a rounded avatar image");

            assert.containsOnce($widgetFirstColumn, '.o_lunch_user_field',
                "should have a user field");
            assert.containsNone($widgetFirstColumn, '.o_lunch_user_field > .o_field_widget',
                "shouldn't have a field widget in the user field");
            assert.strictEqual($widgetFirstColumn.find('.o_lunch_user_field').text().trim(), "Marc Demo",
                "should have 'Marc Demo' in the user field");

            assert.containsOnce($widgetFirstColumn, '.o_lunch_location_field',
                "should have a location field");
            assert.containsOnce($widgetFirstColumn, '.o_lunch_location_field > .o_field_many2one[name="locations"]',
                "should have a many2one in the location field");

            await testUtils.fields.many2one.clickOpenDropdown('locations');
            const $input = $widgetFirstColumn.find('.o_field_many2one[name="locations"] input');
            assert.containsN($input.autocomplete('widget'), 'li', 2,
                "autocomplete dropdown should have 2 entries");
            assert.strictEqual($input.val(), "Office 2",
                "locations input should have 'Office 2' as value");

            assert.containsOnce($widgetFirstColumn, '.o_lunch_location_field + div',
                "should have an account balance");
            assert.strictEqual($widgetFirstColumn.find('.o_lunch_location_field + div .o_field_monetary').text().trim(), "36.50€",
                "should have '36.50€' in the account balance");

            kanban.destroy();
        });

        QUnit.test('manager user', async function (assert) {
            assert.expect(12);

            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: mockLunchRPC({
                    infos: this.managerInfos,
                    userLocation: this.data['lunch.location'].records[0].id,
                }),
            });

            const $kanbanWidget = kanban.$('.o_lunch_widget');

            assert.containsOnce($kanbanWidget, '.o_lunch_widget_info:first',
                "should have a first column");

            const $widgetFirstColumn = $kanbanWidget.find('.o_lunch_widget_info:first');

            assert.containsOnce($widgetFirstColumn, 'img.rounded-circle',
                "should have a rounded avatar image");

            assert.containsOnce($widgetFirstColumn, '.o_lunch_user_field',
                "should have a user field");
            assert.containsOnce($widgetFirstColumn, '.o_lunch_user_field > .o_field_many2one[name="users"]',
                "shouldn't have a field widget in the user field");

            await testUtils.fields.many2one.clickOpenDropdown('users');
            const $userInput = $widgetFirstColumn.find('.o_field_many2one[name="users"] input');
            assert.containsN($userInput.autocomplete('widget'), 'li', 2,
                "users autocomplete dropdown should have 2 entries");
            assert.strictEqual($userInput.val(), "Mitchell Admin",
                "should have 'Mitchell Admin' as value in user field");

            assert.containsOnce($widgetFirstColumn, '.o_lunch_location_field',
                "should have a location field");
            assert.containsOnce($widgetFirstColumn, '.o_lunch_location_field > .o_field_many2one[name="locations"]',
                "should have a many2one in the location field");

            await testUtils.fields.many2one.clickOpenDropdown('locations');
            const $locationInput = $widgetFirstColumn.find('.o_field_many2one[name="locations"] input');
            assert.containsN($locationInput.autocomplete('widget'), 'li', 2,
                "locations autocomplete dropdown should have 2 entries");
            assert.strictEqual($locationInput.val(), "Office 2",
                "should have 'Office 2' as value");

            assert.containsOnce($widgetFirstColumn, '.o_lunch_location_field + div',
                "should have an account balance");
                assert.strictEqual($widgetFirstColumn.find('.o_lunch_location_field + div .o_field_monetary').text().trim(), "47.60€",
                    "should have '47.60€' in the account balance");

            kanban.destroy();
        });

        QUnit.test('add a product', async function (assert) {
            assert.expect(1);

            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: mockLunchRPC({
                    infos: this.regularInfos,
                    userLocation: this.data['lunch.location'].records[0].id,
                }),
                intercepts: {
                    do_action: function (ev) {
                        assert.deepEqual(ev.data.action, {
                            name: "Configure Your Order",
                            res_model: 'lunch.order.temp',
                            type: 'ir.actions.act_window',
                            views: [[false, 'form']],
                            target: 'new',
                            context: {
                                default_product_id: 1,
                                line_id: false,
                            },
                        },
                        "should open the wizard");
                    },
                },
            });

            await testUtils.dom.click(kanban.$('.o_kanban_record:first'));

            kanban.destroy();
        });

        QUnit.test('add product quantity', async function (assert) {
            assert.expect(3);

            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: Object.assign({}, this.data, {
                    'lunch.order': {
                        fields: {},
                        update_quantity([lineIds, increment]) {
                            assert.deepEqual(lineIds, [6], "should have [6] as lineId to update quantity");
                            assert.strictEqual(increment, 1, "should have +1 as increment to update quantity");
                            return Promise.resolve();
                        },
                    },
                }),
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: mockLunchRPC({
                    infos: Object.assign({}, this.regularInfos, {
                        lines: [
                            {
                                id: 6,
                                product: [1, "Tuna sandwich", "3.00"],
                                toppings: [],
                                quantity: 1.0,
                            },
                        ],
                    }),
                    userLocation: this.data['lunch.location'].records[0].id,
                }),
            });

            const $widgetSecondColumn = kanban.$('.o_lunch_widget .o_lunch_widget_info:eq(1)');

            assert.containsOnce($widgetSecondColumn, '.o_lunch_widget_lines > li',
                "should have 1 order line");

            const $firstLine = $widgetSecondColumn.find('.o_lunch_widget_lines > li:first');

            await testUtils.dom.click($firstLine.find('button.o_add_product'));

            kanban.destroy();
        });

        QUnit.test('remove product quantity', async function (assert) {
            assert.expect(3);

            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: Object.assign({}, this.data, {
                    'lunch.order': {
                        fields: {},
                        update_quantity([lineIds, increment]) {
                            assert.deepEqual(lineIds, [6], "should have [6] as lineId to update quantity");
                            assert.strictEqual(increment, -1, "should have -1 as increment to update quantity");
                            return Promise.resolve();
                        },
                    },
                }),
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: mockLunchRPC({
                    infos: Object.assign({}, this.regularInfos, {
                        lines: [
                            {
                                id: 6,
                                product: [1, "Tuna sandwich", "3.00"],
                                toppings: [],
                                quantity: 1.0,
                            },
                        ],
                    }),
                    userLocation: this.data['lunch.location'].records[0].id,
                }),
            });

            const $widgetSecondColumn = kanban.$('.o_lunch_widget .o_lunch_widget_info:eq(1)');

            assert.containsOnce($widgetSecondColumn, '.o_lunch_widget_lines > li',
                "should have 1 order line");

            const $firstLine = $widgetSecondColumn.find('.o_lunch_widget_lines > li:first');

            await testUtils.dom.click($firstLine.find('button.o_remove_product'));

            kanban.destroy();
        });

        QUnit.test('clear order', async function (assert) {
            assert.expect(1);

            const self = this;
            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: function (route) {
                    if (route.startsWith('/lunch')) {
                        if (route === '/lunch/trash') {
                            assert.ok('should perform clear order RPC call');
                            return Promise.resolve();
                        }
                        return mockLunchRPC({
                            infos: Object.assign({}, self.regularInfos, {
                                lines: [
                                    {
                                        product: [1, "Tuna sandwich", "3.00"],
                                        toppings: [],
                                    },
                                ],
                            }),
                            userLocation: self.data['lunch.location'].records[0].id,
                        }).apply(this, arguments);
                    }
                    return this._super.apply(this, arguments);
                },
            });

            const $widgetSecondColumn = kanban.$('.o_lunch_widget .o_lunch_widget_info:eq(1)');

            await testUtils.dom.click($widgetSecondColumn.find('button.o_lunch_widget_unlink'));

            kanban.destroy();
        });

        QUnit.test('validate order: success', async function (assert) {
            assert.expect(1);

            const self = this;
            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: function (route) {
                    if (route.startsWith('/lunch')) {
                        if (route === '/lunch/pay') {
                            assert.ok("should perform pay order RPC call");
                            return Promise.resolve(true);
                        }
                        return mockLunchRPC({
                            infos: Object.assign({}, self.regularInfos, {
                                lines: [
                                    {
                                        product: [1, "Tuna sandwich", "3.00"],
                                        toppings: [],
                                    },
                                ],
                            }),
                            userLocation: self.data['lunch.location'].records[0].id,
                        }).apply(this, arguments);
                    }
                    return this._super.apply(this, arguments);
                },
            });

            const $widgetThirdColumn = kanban.$('.o_lunch_widget .o_lunch_widget_info:eq(2)');

            await testUtils.dom.click($widgetThirdColumn.find('button.o_lunch_widget_order_button'));

            kanban.destroy();
        });

        QUnit.test('validate order: failure', async function (assert) {
            assert.expect(5);

            const self = this;
            const kanban = await createLunchKanbanView({
                View: LunchKanbanView,
                model: 'product',
                data: this.data,
                arch: `
                    <kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="name"/></div>
                            </t>
                        </templates>
                    </kanban>
                `,
                mockRPC: function (route) {
                    if (route.startsWith('/lunch')) {
                        if (route === '/lunch/pay') {
                            assert.ok('should perform pay order RPC call');
                            return Promise.resolve(false);
                        }
                        if (route === '/lunch/payment_message') {
                            assert.ok('should perform payment message RPC call');
                            return Promise.resolve({ message: 'This is a payment message.'});
                        }
                        return mockLunchRPC({
                            infos: Object.assign({}, self.regularInfos, {
                                lines: [
                                    {
                                        product: [1, "Tuna sandwich", "3.00"],
                                        toppings: [],
                                    },
                                ],
                            }),
                            userLocation: self.data['lunch.location'].records[0].id,
                        }).apply(this, arguments);
                    }
                    return this._super.apply(this, arguments);
                },
            });

            const $widgetThirdColumn = kanban.$('.o_lunch_widget .o_lunch_widget_info:eq(2)');

            await testUtils.dom.click($widgetThirdColumn.find('button.o_lunch_widget_order_button'));

            assert.containsOnce(document.body, '.modal', "should open a Dialog box");
            assert.strictEqual($('.modal-title').text().trim(),
                "Not enough money in your wallet", "should have a Dialog's title");
            assert.strictEqual($('.modal-body').text().trim(),
                "This is a payment message.", "should have a Dialog's message");

            kanban.destroy();
        });
    });
});

});
