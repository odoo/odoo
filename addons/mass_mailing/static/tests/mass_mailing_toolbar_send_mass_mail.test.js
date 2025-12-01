import { describe, expect, test, queryOne } from "@odoo/hoot";
import {
    defineModels,
    fields,
    models,
    onRpc,
    defineActions,
    getService,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { defineMailModels, mailModels } from "@mail/../tests/mail_test_helpers";
import { WebClient } from "@web/webclient/webclient";

class Mailing extends models.Model {
    _name = "mailing.mailing";

    mailing_model_id = fields.Many2one({ relation: "ir.model", string: "Recipients" });
    mailing_model_name = fields.Char({ string: "Recipients Model Name" });
    mailing_domain = fields.Char({ string: "Domain" });
    contact_list_ids = fields.Many2many({ relation: "mailing.list", string: "Mailing Lists" });

    _views = {
        form: `
            <form>
                <h3>This is the mailing form</h3>
                <field name="mailing_model_name"/>
                <field name="mailing_model_id"/>
                <field name="contact_list_ids" widget="many2many_tags" invisible="mailing_model_name != 'mailing.list'"/>
                <field name="mailing_domain" widget="domain" options="{'model': 'mailing_model_name'}" invisible="mailing_model_name == 'mailing.list'"/>
            </form>
        `,
    };
}

class MailingList extends models.Model {
    _name = "mailing.list";

    name = fields.Char();

    _records = [
        { id: 1, name: "Interested in Tree Promotions" },
        { id: 2, name: "Imported Contacts" },
        { id: 3, name: "Newsletter Subscribers" },
    ];
}

mailModels.ResPartner._records.push(
    { id: 101, name: "Azure Interior" },
    { id: 102, name: "Acme Corporation" },
    { id: 103, name: "Marc Demo" }
);

mailModels.MailComposeMessage.composition_mode = fields.Selection({
    selection: [
        ["comment", "Post on a document"],
        ["mass_mail", "Email Mass Mailing"],
    ],
});
mailModels.MailComposeMessage._views = {
    form: `
        <form>
            <h3>Compose Message Form</h3>
            <field name="composition_mode"/>
        </form>
    `,
};

defineMailModels();
defineModels([Mailing, MailingList]);
defineActions([
    {
        id: 1,
        name: "Send Email",
        type: "ir.actions.client",
        target: "current",
        tag: "toolbar_send_mass_mail",
    },
]);

describe.current.tags("desktop");

test("Test mass_mailing Send Email toolbar action - Partner", async () => {
    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);

    await getService("action").doAction(1, {
        additionalContext: {
            active_model: "res.partner",
            active_ids: [102, 103],
        },
    });

    expect(".o_model_field_selector_chain_part").toHaveCount(1);
    expect(".o_tag_badge_text").toHaveCount(2);
    expect(".o_tag_badge_text:contains('101')").toHaveCount(0);
    expect(".o_tag_badge_text:contains('102')").toHaveCount(1);
    expect(".o_tag_badge_text:contains('103')").toHaveCount(1);
});

test("Test mass_mailing Send Email toolvar action - Mailing List", async () => {
    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);

    await getService("action").doAction(1, {
        additionalContext: {
            active_model: "mailing.list",
            active_ids: [1, 2],
        },
    });

    expect(".o_tag_badge_text").toHaveCount(2);
    expect(".o_tag_badge_text:contains('Interested in Tree Promotions')").toHaveCount(1);
    expect(".o_tag_badge_text:contains('Imported Contacts')").toHaveCount(1);
    expect(".o_tag_badge_text:contains('Newsletter')").toHaveCount(0);
});

test("Test mass_mailing Send Email toolbar action - Not a mailing user", async () => {
    onRpc("has_group", () => false);
    await mountWithCleanup(WebClient);

    await getService("action").doAction(1, {
        additionalContext: {
            active_model: "mailing.list",
            active_ids: [1, 2],
        },
    });

    expect("h3:contains('This is the mailing form')").toHaveCount(0);
    expect("h3:contains('Compose Message Form'").toHaveCount(1);
    const el = queryOne(".o_field_selection input");
    expect(el).toHaveValue("Email Mass Mailing");
});
