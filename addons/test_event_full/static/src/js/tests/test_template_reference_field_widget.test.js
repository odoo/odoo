import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { click, select } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class EventMail extends models.Model {
    _name = "event.mail";

    template_ref = fields.Reference({
        selection: [
            ["mail.template", "Mail Template"],
            ["sms.template", "SMS Template"],
            ["some.template", "Some Template"],
        ],
    });

    _records = [
        {
            id: 1,
            template_ref: "mail.template,1",
        },
        {
            id: 2,
            template_ref: "sms.template,1",
        },
        {
            id: 3,
            template_ref: "some.template,1",
        },
    ];
}
class MailTemplate extends models.Model {
    _name = "mail.template";

    name = fields.Char();

    _records = [{ id: 1, name: "Mail Template 1" }];
}
class SmsTemplate extends models.Model {
    _name = "sms.template";

    name = fields.Char();

    _records = [{ id: 1, name: "SMS template 1" }];
}
class SomeTemplate extends models.Model {
    _name = "some.template";

    name = fields.Char();

    _records = [{ id: 1, name: "Some Template 1" }];
}
defineMailModels();
defineModels([EventMail, MailTemplate, SmsTemplate, SomeTemplate]);

describe.current.tags("desktop");

test("Reference field displays right icons", async () => {
    // bypass list controller check
    onRpc("has_group", () => true);

    await mountView({
        type: "list",
        resModel: "event.mail",
        arch: `
        <list editable="top">
            <field name="template_ref" widget="EventMailTemplateReferenceField"/>
        </list>`,
    });

    // each field cell will be the field of a different record (1 field/line)
    expect(".o_field_cell").toHaveCount(3);
    expect(".o_field_cell.o_EventMailTemplateReferenceField_cell").toHaveCount(3);
    expect(".o_field_cell:eq(0) .fa-envelope").toHaveCount(1);
    expect(".o_field_cell:eq(1) .fa-mobile").toHaveCount(1);
    expect(".o_field_cell:eq(2) .fa-envelope").toHaveCount(0);
    expect(".o_field_cell:eq(2) .fa-mobile").toHaveCount(0);

    // select a sms.template instead of mail.template

    await click(".o_field_cell:eq(0)");
    await animationFrame();
    await click(".o_field_cell:eq(0) select.o_input");
    await select("sms.template");
    await animationFrame();
    await click(".o_field_cell:eq(0) .o_field_many2one_selection input");
    await animationFrame();
    await click(".o_field_cell:eq(0) .o-autocomplete--dropdown-item");
    // click out
    await click(".o_list_renderer");
    await animationFrame();

    expect(".o_field_cell:eq(0) .fa-mobile").toHaveCount(1);
    expect(".o_field_cell:eq(0) .fa-envelope").toHaveCount(0);

    // select a some other model to check it has no icon

    await click(".o_field_cell:eq(0)");
    await animationFrame();
    await click(".o_field_cell:eq(0) select.o_input");
    await select("some.template");
    await animationFrame();
    await click(".o_field_cell:eq(0) .o_field_many2one_selection input");
    await animationFrame();
    await click(".o_field_cell:eq(0) .o-autocomplete--dropdown-item");
    await click(".o_list_renderer");
    await animationFrame();

    expect(".o_field_cell:eq(0) .fa-mobile").toHaveCount(0);
    expect(".o_field_cell:eq(0) .fa-envelope").toHaveCount(0);

    // select no record for the model

    await click(".o_field_cell:eq(1)");
    await animationFrame();
    await click(".o_field_cell:eq(1) select.o_input");
    await select("mail.template");
    await click(".o_list_renderer");
    await animationFrame();

    expect(".o_field_cell:eq(1) .fa-mobile").toHaveCount(0);
    expect(".o_field_cell:eq(1) .fa-envelope").toHaveCount(0);
});
