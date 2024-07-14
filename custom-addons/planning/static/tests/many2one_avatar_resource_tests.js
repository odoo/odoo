/** @odoo-module **/

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { getFixture } from "@web/../tests/helpers/utils";

let target;

QUnit.module("M2OResourceWidgetTests", {
    beforeEach() {
        this.serverData = {
            models: {
                planning: {
                    fields: {
                        display_name: { string: "Resource Type", type: "char" },
                        resource_type: { string: "Resource Type", type: "selection" },
                        resource_id: { string: "Resource", type: 'many2one', relation: 'resource' },
                    },
                    records: [{
                        id: 1,
                        display_name: "Planning Slot",
                        resource_id: 1,
                        resource_type: 'material',
                    }, {
                        id: 2,
                        display_name: "Planning Slot",
                        resource_id: 2,
                        resource_type: 'human',
                    }],
                },
                resource: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        resource_type: { string: "Resource Type", type: "selection" },
                    },
                    records: [{
                        id: 1,
                        name: "Continuity Tester",
                        resource_type: 'material',
                    }, {
                        id: 2,
                        name: "Admin",
                        resource_type: 'human',
                    }],
                },
            },
            views: {},
        };
        target = getFixture();
        setupViewRegistries();
    },
}, () => {
    QUnit.test('many2one_avatar_resource widget in form view', async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            resModel: 'planning',
            serverData: this.serverData,
            arch:
                `<form string="Partners">
                    <field name="display_name"/>
                    <field name="resource_id" widget="many2one_avatar_resource"/>
                </form>`,
            resId: 1,
        });
        assert.hasClass(
            target.querySelector('.o_material_resource'),
            'o_material_resource',
            "material icon should be displayed"
        );
    });

    QUnit.test('many2one_avatar_resource widget in kanban view', async function (assert) {
        assert.expect(4);

        await makeView({
            type: "kanban",
            resModel: 'planning',
            serverData: this.serverData,
            arch: `<kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="resource_id" widget="many2one_avatar_resource" options="{'hide_label': true}"/></div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.containsN(target, '.o_m2o_avatar', 2);
        assert.hasClass(
            target.querySelector('.o_kanban_record:nth-of-type(1) .o_m2o_avatar > span'),
            'o_material_resource',
            "material icon should be displayed"
        );
        assert.containsOnce(
            target,
            ".o_field_many2one_avatar_resource img",
        );
        assert.strictEqual(
            target.querySelector(".o_field_many2one_avatar_resource img").getAttribute("data-src"),
            "/web/image/resource/2/avatar_128",
        );
    });
});
