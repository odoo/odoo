import { expect, describe, test } from "@odoo/hoot";

import { mountView } from "@web/../tests/web_test_helpers";

import { defineHelpdeskModels } from "@helpdesk/../tests/helpdesk_test_helpers";

describe.current.tags("desktop");
defineHelpdeskModels();

const formViewArch = `
    <form>
        <field name="name" />
        <field name="sla_status_ids"  widget="helpdesk_sla_many2many_tags" options="{ 'color_field': 'color' }"/>
    </form>
`;

test("sla tags icon is rendered according to status and o_field_many2many_tags_avatar class is set", async () => {
    await mountView({
        resModel: "helpdesk.ticket",
        type: "form",
        resId: 1,
        arch: formViewArch,
    });
    expect(".o_field_tags .badge:first-of-type > i:first-child.fa-times-circle").toHaveCount(1);
    expect(".o_field_tags .badge:nth-of-type(2) > i:first-child.fa-check-circle").toHaveCount(1);
    expect(".o_field_tags .badge:nth-of-type(3) > i:first-child").toHaveCount(1);
});

test("o_field_many2many_tags_avatar class is set", async () => {
    await mountView({
        resModel: "helpdesk.ticket",
        type: "form",
        resId: 1,
        arch: formViewArch,
    });
    expect(
        "div[name='sla_status_ids'].o_field_helpdesk_sla_many2many_tags.o_field_many2many_tags"
    ).toHaveCount(1);
});
