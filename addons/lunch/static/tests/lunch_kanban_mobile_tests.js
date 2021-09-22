odoo.define('lunch.lunchKanbanMobileTests', function (require) {
"use strict";

const LunchKanbanView = require('lunch.LunchKanbanView');

const testUtils = require('web.test_utils');
const {createLunchView, mockLunchRPC} = require('lunch.test_utils');

QUnit.module('Views');

QUnit.module('LunchKanbanView Mobile', {
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
            'lunch.location': {
                fields: {
                    name: {string: 'Name', type: 'char'},
                },
                records: [
                    {id: 1, name: "Office 1"},
                    {id: 2, name: "Office 2"},
                ],
            },
        };
        this.regularInfos = {
            user_location: [2, "Office 2"],
        };
    },
}, function () {
    QUnit.test('basic rendering', async function (assert) {
        assert.expect(7);

        const kanban = await createLunchView({
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
        assert.containsOnce(kanban, '.o_content > .o_lunch_content',
            "should have a 'kanban lunch wrapper' column");
        assert.containsOnce(kanban, '.o_lunch_content > .o_kanban_view',
            "should have a 'classical kanban view' column");
        assert.hasClass(kanban.$('.o_kanban_view'), 'o_lunch_kanban_view',
            "should have classname 'o_lunch_kanban_view'");
        assert.containsOnce($('.o_lunch_content'), '> details',
            "should have a 'lunch kanban' details/summary discolure panel");
        assert.hasClass($('.o_lunch_content > details'), 'fixed-bottom',
            "should have classname 'fixed-bottom'");
        assert.isNotVisible($('.o_lunch_content > details .o_lunch_banner'),
            "shouldn't have a visible 'lunch kanban' banner");

        kanban.destroy();
    });

    QUnit.module('LunchWidget', function () {
        QUnit.test('toggle', async function (assert) {
            assert.expect(6);

            const kanban = await createLunchView({
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
                    }),
                    userLocation: this.data['lunch.location'].records[0].id,
                }),
            });

            const $details = $('.o_lunch_content > details');
            assert.isNotVisible($details.find('.o_lunch_banner'),
                "shouldn't have a visible 'lunch kanban' banner");
            assert.isVisible($details.find('> summary'),
                "should hava a visible cart toggle button");
            assert.containsOnce($details, '> summary:contains(Your cart)',
                "should have 'Your cart' in the button text");
            assert.containsOnce($details, '> summary:contains(3.00)',
                "should have '3.00' in the button text");

            await testUtils.dom.click($details.find('> summary'));
            assert.isVisible($details.find('.o_lunch_banner'),
                "should have a visible 'lunch kanban' banner");

            await testUtils.dom.click($details.find('> summary'));
            assert.isNotVisible($details.find('.o_lunch_banner'),
                "shouldn't have a visible 'lunch kanban' banner");

            kanban.destroy();
        });

        QUnit.test('keep open when adding quantities', async function (assert) {
            assert.expect(6);

            const kanban = await createLunchView({
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

            const $details = $('.o_lunch_content > details');
            assert.isNotVisible($details.find('.o_lunch_banner'),
                "shouldn't have a visible 'lunch kanban' banner");
            assert.isVisible($details.find('> summary'),
                "should hava a visible cart toggle button");

            await testUtils.dom.click($details.find('> summary'));
            assert.isVisible($details.find('.o_lunch_banner'),
                "should have a visible 'lunch kanban' banner");

            const $widgetSecondColumn = kanban.$('.o_lunch_widget .o_lunch_widget_info:eq(1)');

            assert.containsOnce($widgetSecondColumn, '.o_lunch_widget_lines > li',
                "should have 1 order line");

            let $firstLine = $widgetSecondColumn.find('.o_lunch_widget_lines > li:first');

            await testUtils.dom.click($firstLine.find('button.o_add_product'));
            assert.isVisible($('.o_lunch_content > details .o_lunch_banner'),
                "add quantity should keep 'lunch kanban' banner open");

            $firstLine = kanban.$('.o_lunch_widget .o_lunch_widget_info:eq(1) .o_lunch_widget_lines > li:first');

            await testUtils.dom.click($firstLine.find('button.o_remove_product'));
            assert.isVisible($('.o_lunch_content > details .o_lunch_banner'),
                "remove quantity should keep 'lunch kanban' banner open");

            kanban.destroy();
        });
    });
});

});
