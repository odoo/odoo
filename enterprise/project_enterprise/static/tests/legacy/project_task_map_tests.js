/* @odoo-module */

import { setupViewRegistries, makeView } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";

import { getFixture } from "@web/../tests/helpers/utils";
import { makeFakeHTTPService } from "@web/../tests/helpers/mock_services";

let serverData;
let target;
const serviceRegistry = registry.category("services");

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();

        serverData = {             
            models: {
                "project.task": {
                    fields: {
                        id: { string: "Id", type: "integer" },
                        display_name: { string: "Name", type: "char" },
                        partner_id: {
                            string: "Customer",
                            type: "many2one",
                            relation: "res.partner",
                        },
                        planned_date_begin: { string: "Schedule date", type: "datetime" },
                    },
                    records: [
                        { 
                            id: 1, 
                            display_name: "Unscheduled task", 
                            partner_id: 1,
                        },
                        { 
                            id: 2,
                            display_name: "Scheduled task",
                            partner_id: 1,
                            planned_date_begin: "2023-10-18 06:30:12",
                        },
                    ],
                },
                "res.partner": {
                    fields: {
                        name: { string: "Customer", type: "char" },
                        partner_latitude: { string: "Latitude", type: "float" },
                        partner_longitude: { string: "Longitude", type: "float" },
                        contact_address_complete: { string: "Address", type: "char" },
                        task_ids: {
                            string: "Task",
                            type: "one2many",
                            relation: "project.task",
                            relation_field: "partner_id",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            name: "Foo",
                            partner_latitude: 10.0,
                            partner_longitude: 10.5,
                            contact_address_complete: "Chaussée de Namur 40, 1367, Ramillies",
                        },
                    ]
                }
            }
        }

        serviceRegistry.add("http", makeFakeHTTPService());
        setupViewRegistries();

    });
    QUnit.module("MapView");

    QUnit.test("Test muted label for unplanned task in map", async function (assert) {
        assert.expect(2);

        await makeView({
            serverData,
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" js_class="project_task_map">
                        <field name="partner_id" string="Customer"/>
                        <field name="planned_date_begin" string="Date"/>
                    </map>`,
        });

        assert.containsOnce(target, '.o-map-renderer--pin-list-details li.text-muted:contains("Unscheduled task")', "The name of the unscheduled task should be muted");
        assert.containsOnce(target, '.o-map-renderer--pin-list-details li:not(.text-muted):contains("Scheduled task")', "The name of the scheduled task shouldn't be muted");
    });
});
