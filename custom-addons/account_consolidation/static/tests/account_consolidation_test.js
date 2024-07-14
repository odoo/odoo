/** @odoo-module **/
import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module('Consolidation Tests', {}, function() {

    QUnit.module("Fields");

    QUnit.test('render json field', async function (assert) {
        assert.expect(1);
        let target = getFixture();
        setupViewRegistries();

        await makeView({
            type: "kanban",
            resModel: "consolidation",
            serverData: {
                models: {
                    'consolidation': {
                        fields: {
                            json: { string: "Json", type: "text" },
                        },
                        records: [
                            {
                                id: 1,
                                json: '[]'
                            },
                            {
                                id: 2,
                                json: '[{"name": "Section 1", "value": "125.00 €"},{"name": "Section 2","value": "294.00 €"}]',
                            }
                        ],
                    },
                },
                views: { },
            },
            arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="json" widget="consolidation_dashboard_field"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        });
        assert.containsN(
            target,
            ".o_field_consolidation_dashboard_field",
            2,
            "Both records are rendered"
        );
    });
});
