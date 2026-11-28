import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class MailAliasDomain extends models.Model {
    _name = "mail.alias.domain";

    name = fields.Char();

    _records = [{ id: 1, name: "example.com" }];
}

class MailAlias extends models.Model {
    _name = "mail.alias";

    name = fields.Char();

    _records = [{ id: 1, name: "bills@example.com" }];
}

class AccountJournal extends models.Model {
    _name = "account.journal";

    type = fields.Char();
    alias_domain_id = fields.Many2one({ relation: "mail.alias.domain" });
    alias_id = fields.Many2one({ relation: "mail.alias" });

    _records = [{ id: 1, type: "purchase", alias_domain_id: 1, alias_id: 1 }];
}

defineModels([MailAliasDomain, MailAlias, AccountJournal]);
defineMailModels();

test("bill guide shows the email alias of the journal", async () => {
    onRpc("account.journal", "is_sample_action_available", () => false);
    await mountView({
        type: "form",
        resModel: "account.journal",
        resId: 1,
        arch: `
            <form>
                <field name="type"/>
                <field name="alias_domain_id"/>
                <field name="alias_id"/>
                <widget name="bill_upload_guide"/>
            </form>`,
    });
    expect(".bill_guide_right a[href='mailto:bills@example.com']").toHaveText("bills@example.com");
});
