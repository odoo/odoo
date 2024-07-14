/** @odoo-module */

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;

QUnit.module('Marketing Automation', (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                campaign: {
                    fields: {
                        name: {string : "Campaign Name", type: "char"},
                        marketing_activity_ids: {string : "Activities", relation: 'activity', type: 'one2many', relation_field: 'campaign_id',},
                    },
                    records: [{
                        id: 1,
                        name: 'Campaign 1',
                        marketing_activity_ids: [1, 2, 3, 4, 5, 6],
                    }]
                },
                activity: {
                    fields: {
                        name: {string : "Activity Name", type: "char"},
                        parent_id: {string : "Parent Activity", relation: 'activity', type: 'many2one'},
                        campaign_id: {string : "Campaign", relation: 'campaign', type: 'many2one'},
                    },
                    records: [{
                        id: 1,
                        name: 'Parent 1',
                    }, {
                        id: 2,
                        name: 'Parent 1 > Child 1',
                        parent_id: 1,
                    }, {
                        id: 3,
                        name: 'Parent 2',
                    }, {
                        id: 4,
                        name: 'Parent 2 > Child 1',
                        parent_id: 3,
                    }, {
                        id: 5,
                        name: 'Parent 2 > Child 2',
                        parent_id: 3
                    }, {
                        id: 6,
                        name: 'Parent 2 > Child 2 > Child 1',
                        parent_id: 5
                    }]
                }
            }
        };
        setupViewRegistries();
    });

    QUnit.test('render basic hirarchy kanban', async function (assert) {
        assert.expect(9);

        await makeView({
            type: "form",
            resModel: 'campaign',
            serverData,
            arch: '<form string="Campaign">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="name"/>' +
                        '</group>' +
                        '<div>' +
                            '<field name="marketing_activity_ids" widget="hierarchy_kanban" class="o_ma_hierarchy_container">' +
                                '<kanban>' +
                                    '<field name="id"/>' +
                                    '<field name="name"/>' +
                                    '<field name="parent_id"/>' +
                                    '<templates>' +
                                        '<div t-name="kanban-box">' +
                                            '<div class="o_ma_body position-relative" t-att-data-record-id="record.id.raw_value">' +
                                                '<div class="o_title">' +
                                                    '<t t-esc="record.name.value"/>' +
                                                '</div>' +
                                            '</div>' +
                                        '</div>' +
                                    '</templates>' +
                                '</kanban>' +
                            '</field>' +
                        '</div>' +
                    '</sheet>' +
                '</form>',
            resId: 1
        });

        // Checking number of child and their positions
        const parentRecords = target
            .querySelectorAll('.o_ma_hierarchy_container .o_kanban_renderer > .o_kanban_record:not(.o_kanban_ghost):not(:empty) > .o_ma_body');
        const childrenRecords = target
            .querySelectorAll('.o_ma_hierarchy_container .o_kanban_renderer > .o_kanban_record:not(.o_kanban_ghost):not(:empty) > .o_ma_body_wrapper > .o_ma_body');
        const grandChildrenRecords = target
            .querySelectorAll('.o_ma_hierarchy_container .o_kanban_renderer > .o_kanban_record:not(.o_kanban_ghost):not(:empty) > .o_ma_body_wrapper > .o_ma_body_wrapper > .o_ma_body');
        assert.strictEqual(parentRecords.length, 2, "There should be 2 parents");
        assert.strictEqual(childrenRecords.length, 3, "There should be 3 children");
        assert.strictEqual(grandChildrenRecords.length, 1, "There should be 1 grand-child");

        // Checking titles of kanban to verify proper values
        assert.strictEqual(
            parentRecords[0].querySelector(':scope .o_title').innerText,
            'Parent 1',
            "Title of 1st parent");
        assert.strictEqual(
            parentRecords[1].querySelector(':scope .o_title').innerText,
            'Parent 2',
            "Title of 2nd parent");
        assert.strictEqual(
            childrenRecords[0].querySelector(':scope .o_title').innerText,
            'Parent 1 > Child 1',
            "Title of 1st parent's child");
        assert.strictEqual(
            childrenRecords[1].querySelector(':scope .o_title').innerText,
            'Parent 2 > Child 1',
            "Title of 2nd parent's 1st child");
        assert.strictEqual(
            childrenRecords[2].querySelector(':scope > .o_title').innerText,
            'Parent 2 > Child 2',
            "Title of 2nd parent's 2nd child");
        assert.strictEqual(
            grandChildrenRecords[0].querySelector(':scope > .o_title').innerText,
            'Parent 2 > Child 2 > Child 1',
            "Title of 2nd parent's 2nd child's 1st child");
    });
});
