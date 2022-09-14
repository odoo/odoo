/** @odoo-module **/

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { clickDropdown, clickEdit, getFixture } from "@web/../tests/helpers/utils";


QUnit.module('sale_expense', {
    beforeEach: function () {
        this.target = getFixture();
        this.data = {
        }
        this.data = {
            models: {
                'hr.expense': {
                    fields: {
                        name: { string: "Description", type: "char" },
                        sale_order_id: { string: "Reinvoice Customer", type: 'many2one', relation: 'sale.order' },
                    },
                    records: [{id: 1}]
                },
                'sale.order': {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [{
                        id: 1,
                        name: "SO1",
                    }, {
                        id: 2,
                        name: "SO2",
                    }, {
                        id: 3,
                        name: "SO3"
                    }, {
                        id: 4,
                        name: "SO4"
                    }, {
                        id: 5,
                        name: "SO5"
                    }, {
                        id: 6,
                        name: "SO6"
                    }, {
                        id: 7,
                        name: "SO7"
                    }, {
                        id: 8,
                        name: "SO8"
                    }, {
                        id: 9,
                        name: "SO9"
                    }]
                },
            }
        };
        setupViewRegistries();
    },
}, function () {
    QUnit.test('sale order many2one without search more option', async function (assert) {
        assert.expect(2);
        await makeView({
            type: "form",
            resModel: "hr.expense",
            serverData: this.data,
            resId: 1,
            arch:
                '<form><field name="sale_order_id" widget="sale_order_many2one"/></form>'
        });

        await clickEdit(this.target);
        await clickDropdown(this.target, "sale_order_id");

        assert.containsN(this.target, 'li.o-autocomplete--dropdown-item', 9);
        assert.containsNone(this.target, '.o_m2o_dropdown_option_search_more', "Should not display the 'Search More... option'");
    });
});
