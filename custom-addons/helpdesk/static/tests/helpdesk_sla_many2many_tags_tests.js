/** @odoo-module **/

import { getFixture } from '@web/../tests/helpers/utils';
import { makeView, setupViewRegistries } from '@web/../tests/views/helpers';


QUnit.module("helpdesk", { }, function () {
    let target;
    let serverData;
    QUnit.module("sla_many2many_tags", {
        async beforeEach() {
            serverData = {
                models: {
                    "helpdesk.ticket": {
                        fields: {
                            id: { string: "Id", type: "integer" },
                            name: { string: "Name", type: "string" },
                            sla_status_ids: { string: "SLA's", type: "one2many", relation: "helpdesk.sla.status" },
                        },
                        records: [
                            { id: 1, name: "My ticket", sla_status_ids: [1, 2, 3] },
                        ],
                    },
                    "helpdesk.sla.status": {
                        fields: {
                            id: { string: "Id", type: "integer" },
                            color: { string: "Color index", type: "integer" },
                            name: { string: "Name", type: "string" },
                            status: {
                                string: "Status",
                                type: "selection",
                                selection: [["failed", "Failed"], ["reached", "Reached"], ["dummy", "Dummy"]],
                            },
                            ticket_id: { string: "Ticket", type: "many2one", relation: "helpdesk.ticket" },
                        },
                        records: [
                            { id: 1, color: 1, name: "SLA Status 1", status: "failed", ticket_id: 1 },
                            { id: 2, color: 2, name: "SLA Status 2", status: "reached", ticket_id: 1 },
                            { id: 3, color: 3, name: "SLA Status 3", status: "dummy", ticket_id: 1 },
                        ],
                    },
                },
                views: {
                    "helpdesk.ticket,false,form": `
                        <form>
                            <sheet>
                                <field name="sla_status_ids" class="o_field_many2many_tags" widget="helpdesk_sla_many2many_tags" options="{ 'color_field': 'color' }"/>
                            </sheet>
                        </form>
                    `,
                },
            };
            target = getFixture();
            setupViewRegistries();
        },
    }, function () {
        QUnit.test("sla tags icon is rendered according to status", async (assert) => {
            await makeView({
                type: 'form',
                resModel: 'helpdesk.ticket',
                resId: 1,
                serverData,
            });
            assert.containsOnce(target, ".o_field_tags .badge:first-of-type > i:first-child.fa-times-circle", "failed status triggers the injection of a fa-times-circle icon");
            assert.containsOnce(target, ".o_field_tags .badge:nth-of-type(2) > i:first-child.fa-check-circle", "reached status triggers the injection of a fa-check-circle icon");
            assert.containsNone(target, ".o_field_tags .badge:nth-of-type(3) > i:first-child", "a status other than 'failed' and 'reached' does not trigger the injection of an icon");
        });
        QUnit.test("o_field_many2many_tags_avatar class is set", async (assert) => {
            await makeView({
                type: 'form',
                resModel: 'helpdesk.ticket',
                resId: 1,
                serverData,
            });
            assert.containsOnce(target, "div[name='sla_status_ids'].o_field_helpdesk_sla_many2many_tags.o_field_many2many_tags", "o_field_many2many_tags class is added in order to keep the scss of the many2many_tags widget");
        });
    });
});
