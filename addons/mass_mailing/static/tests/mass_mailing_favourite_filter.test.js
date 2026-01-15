import { expect, test, describe } from "@odoo/hoot";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    contains,
    clickSave,
    MockServer,
} from "@web/../tests/web_test_helpers";
import { queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

class Mailing extends models.Model {
    _name = "mailing.mailing";

    display_name = fields.Char();
    subject = fields.Char();
    mailing_model_id = fields.Many2one({ relation: "ir.model", string: "Recipients" });
    mailing_model_name = fields.Char({ string: "Recipients Model Name" });
    mailing_filter_id = fields.Many2one({ relation: "mailing.filter", string: "Filters" });
    mailing_domain = fields.Char({ string: "Domain" });
    mailing_filter_domain = fields.Char({ related: "mailing_domain", string: "Domain" });
    mailing_filter_count = fields.Integer({ string: "Filter Count" });

    _records = [
        {
            id: 1,
            display_name: "Belgian Event promotion",
            subject: "Early bird discount for Belgian Events! Register Now!",
            mailing_model_id: 1,
            mailing_model_name: "event",
            mailing_domain: '[["country","=","be"]]',
            mailing_filter_id: 1,
            mailing_filter_count: 1,
            mailing_filter_domain: '[["country","=","be"]]',
        },
        {
            id: 2,
            display_name: "New Users Promotion",
            subject: "Early bird discount for new users! Register Now!",
            mailing_model_id: 1,
            mailing_filter_count: 1,
            mailing_model_name: "event",
            mailing_domain: '[["new_user","=",True]]',
            mailing_filter_domain: '[["new_user","=",True]]',
        },
    ];
}

class IrModel extends models.Model {
    _name = "ir.model";

    name = fields.Char();
    model = fields.Char();

    _records = [
        {
            id: 1,
            name: "Event",
            model: "event",
        },
        {
            id: 2,
            name: "Partner",
            model: "partner",
        },
    ];
}

class MailingFilter extends models.Model {
    _name = "mailing.filter";

    name = fields.Char();
    mailing_domain = fields.Char();
    mailing_model_id = fields.Many2one({ relation: "ir.model", string: "Recipients Model" });

    _records = [
        {
            id: 1,
            name: "Belgian Events",
            mailing_domain: '[["country","=","be"]]',
            mailing_model_id: 1,
        },
    ];
}

class Partner extends models.Model {
    _name = "partner";

    name = fields.Char();

    _records = [
        { id: 1, name: "Azure Interior" },
        { id: 2, name: "Deco Addict" },
        { id: 3, name: "Marc Demo" },
    ];
}

class Event extends models.Model {
    _name = "event";

    name = fields.Char();
    country = fields.Char();

    _records = [{ id: 1, name: "BE Event", country: "be" }];
}

defineMailModels();
defineModels([IrModel, Mailing, MailingFilter, Partner, Event]);

describe.current.tags("desktop");

test("create favorite filter", async () => {
    expect.assertions(8);

    onRpc("mailing.filter", "create", (params) => {
        expect(params.args[0]).toEqual([
            {
                mailing_domain: '[["new_user","=",True]]',
                mailing_model_id: 1,
                name: "event promo - new users",
            },
        ]);
    });

    await mountView({
        type: "form",
        resModel: "mailing.mailing",
        resId: 2,
        arch: `<form>
                    <field name="display_name"/>
                    <field name="subject"/>
                    <field name="mailing_domain"/>
                    <field name="mailing_model_name" invisible="1"/>
                    <field name="mailing_model_id"/>
                    <field name="mailing_filter_count"/>
                    <field name="mailing_filter_domain" invisible="1"/>
                    <field name="mailing_filter_id"
                        widget="mailing_filter"
                        options="{'no_create': '1', 'no_open': '1', 'domain_field': 'mailing_domain', 'model': 'mailing_model_id'}"/>
                </form>`,
    });

    queryFirst(".o_field_mailing_filter input").autocomplete = "widget";
    expect(".o_mass_mailing_remove_filter").not.toBeVisible();
    expect(".o_mass_mailing_save_filter_container").toBeVisible();

    await contains(".o_field_mailing_filter input").click();
    expect(".o_field_mailing_filter .dropdown li.ui-menu-item").toHaveCount(2);

    await contains(".o_mass_mailing_add_filter").click();
    await contains(".o_mass_mailing_filter_name").edit("event promo - new users", {
        confirm: "Enter",
    });
    await contains(".o_content").click();

    expect(".o_field_mailing_filter input").toHaveValue("event promo - new users");
    expect(".o_mass_mailing_remove_filter").toBeVisible();
    expect(".o_mass_mailing_save_filter_container").not.toBeVisible();
    await contains(".o_field_mailing_filter input").click();
    expect(".o_field_mailing_filter .dropdown li.ui-menu-item").toHaveCount(3);
    await clickSave();
});

test("unlink favorite filter", async () => {
    expect.assertions(10);

    onRpc("mailing.filter", "unlink", (params) => {
        expect(params.args[0]).toEqual([1]);
    });

    onRpc("mailing.mailing", "web_save", (params) => {
        expect(params.args[1].mailing_filter_id).toBe(false);
        expect(params.args[1].mailing_domain).toBe('[["country","=","be"]]');
    });

    await mountView({
        type: "form",
        resModel: "mailing.mailing",
        resId: 1,
        arch: `<form>
                    <field name="display_name"/>
                    <field name="subject"/>
                    <field name="mailing_domain"/>
                    <field name="mailing_model_name" invisible="1"/>
                    <field name="mailing_model_id"/>
                    <field name="mailing_filter_count"/>
                    <field name="mailing_filter_domain" invisible="1"/>
                    <field name="mailing_filter_id"
                        widget="mailing_filter"
                        options="{'no_create': '1', 'no_open': '1', 'domain_field': 'mailing_domain', 'model': 'mailing_model_id'}"/>
                </form>`,
    });

    expect(".o_field_mailing_filter input").toHaveValue("Belgian Events");
    expect(".o_mass_mailing_remove_filter").toBeVisible();
    expect(".o_mass_mailing_save_filter_container").not.toBeVisible();

    await contains(".o_mass_mailing_remove_filter").click();
    await animationFrame();
    expect(".o_field_mailing_filter input").toHaveValue("");
    expect(".o_mass_mailing_remove_filter").not.toBeVisible();
    expect(".o_mass_mailing_save_filter_container").toBeVisible();

    queryFirst(".o_field_mailing_filter input").autocomplete = "widget";
    await contains(".o_field_mailing_filter input").click();
    expect(".o_field_mailing_filter .dropdown li.ui-menu-item.o_m2o_no_result").toHaveCount(1);
    await clickSave();
});

test("changing filter correctly applies the domain", async () => {
    MailingFilter._records = [
        {
            id: 1,
            name: "Azure Partner Only",
            mailing_domain: "[['name','=', 'Azure Interior']]",
            mailing_model_id: 2,
        },
    ];

    Mailing._records.push({
        id: 3,
        display_name: "Partner Event promotion",
        subject: "Early bird discount for Partners!",
        mailing_model_id: 2,
        mailing_model_name: "partner",
        mailing_filter_count: 1,
        mailing_domain: "[['name','!=', 'Azure Interior']]",
    });

    Mailing._onChanges = {
        mailing_filter_id(record) {
            record.mailing_domain = MockServer.env["mailing.filter"].filter(
                (r) => r.id === record.mailing_filter_id
            )[0].mailing_domain;
        },
    };

    await mountView({
        type: "form",
        resModel: "mailing.mailing",
        resId: 3,
        arch: `<form>
                    <field name="display_name"/>
                    <field name="subject"/>
                    <field name="mailing_model_name" invisible="1"/>
                    <field name="mailing_model_id"/>
                    <field name="mailing_filter_count" />
                    <field name="mailing_filter_id" widget="mailing_filter" options="{'no_create': '1', 'no_open': '1', 'domain_field': 'mailing_domain', 'model': 'mailing_model_id'}"/>
                    <group>
                        <field name="mailing_domain" widget="domain" options="{'model': 'mailing_model_name'}"/>
                    </group>
                </form>`,
    });

    expect(".o_domain_show_selection_button").toHaveText("2 record(s)");
    await contains(".o_field_mailing_filter input").click();
    queryFirst(".o_field_mailing_filter input").autocomplete = "widget";
    await contains(".o_field_mailing_filter .dropdown li:first-of-type").click();
    await animationFrame();
    expect(".o_domain_show_selection_button").toHaveText("1 record(s)");
});

test("filter drop-down and filter icons visibility toggles properly based on filters available", async () => {
    MailingFilter._records = [
        {
            id: 2,
            name: "Azure partner",
            mailing_domain: '[["name","=","Azure Interior"]]',
            mailing_model_id: 2,
        },
        {
            id: 3,
            name: "Ready Mat partner",
            mailing_domain: '[["name","=","Ready Mat"]]',
            mailing_model_id: 2,
        },
    ];

    Mailing._records = [
        {
            id: 1,
            display_name: "Belgian Event promotion",
            subject: "Early bird discount for Belgian Events! Register Now!",
            mailing_model_id: 1,
            mailing_model_name: "event",
            mailing_domain: '[["country","=","be"]]',
            mailing_filter_id: false,
            mailing_filter_count: 0,
        },
    ];

    Mailing._onChanges = {
        mailing_model_id(record) {
            record.mailing_filter_count = MockServer.env["mailing.filter"].filter(
                (r) => r.mailing_model_id === record.mailing_model_id
            ).length;
        },
        mailing_filter_id(record) {
            const filterDomain = MockServer.env["mailing.filter"].filter(
                (r) => r.id === record.mailing_filter_id
            )[0].mailing_domain;
            record.mailing_domain = filterDomain;
            record.mailing_filter_domain = filterDomain;
        },
    };

    await mountView({
        type: "form",
        resModel: "mailing.mailing",
        resId: 1,
        arch: `<form>
                <field name="display_name"/>
                <field name="subject"/>
                <field name="mailing_model_name" invisible="1"/>
                <field name="mailing_model_id"/>
                <field name="mailing_filter_count" />
                <field name="mailing_filter_id" widget="mailing_filter"
                    options="{'no_create': '1', 'no_open': '1', 'domain_field': 'mailing_domain', 'model': 'mailing_model_id'}"/>
                <field name="mailing_filter_domain" invisible="1"/>
                <group>
                    <field name="mailing_domain" widget="domain" options="{'model': 'mailing_model_name'}"/>
                </group>
            </form>`,
    });

    expect(".o_field_mailing_filter .o_input_dropdown").not.toBeVisible();
    expect(".o_mass_mailing_no_filter").toBeVisible();
    expect(".o_mass_mailing_save_filter_container").toBeVisible();

    await contains(".o_tree_editor_node_control_panel > button:nth-child(2)").click();
    expect(".o_field_mailing_filter .o_input_dropdown").not.toBeVisible();
    expect(".o_mass_mailing_filter_container").not.toBeVisible();

    await contains(".o_field_widget[name='mailing_model_id'] input").click();
    await contains(".dropdown-item:contains('Partner')").click();
    expect(".o_field_mailing_filter .o_input_dropdown").toBeVisible();
    expect(".o_mass_mailing_filter_container").not.toBeVisible();

    await contains(".o_field_mailing_filter input").click();
    await contains(".dropdown-item:contains('Azure partner')").click();
    await animationFrame();
    expect(".o_mass_mailing_remove_filter").toBeVisible();
    expect(".o_mass_mailing_save_filter_container").not.toBeVisible();

    await contains(".o_tree_editor_node_control_panel > button:nth-child(1)").click();
    await animationFrame();
    expect(".o_mass_mailing_save_filter_container").toBeVisible();
    expect(".o_mass_mailing_remove_filter").not.toBeVisible();
});

test("filter widget does not raise traceback when losing focus with unexpected domain format", async () => {
    await mountView({
        type: "form",
        resModel: "mailing.mailing",
        resId: 2,
        arch: `<form>
                <field name="display_name"/>
                <field name="subject"/>
                <field name="mailing_domain"/>
                <field name="mailing_model_name" invisible="1"/>
                <field name="mailing_model_id"/>
                <field name="mailing_filter_count"/>
                <field name="mailing_filter_domain" invisible="1"/>
                <field name="mailing_filter_id"
                    widget="mailing_filter"
                    options="{'no_create': '1', 'no_open': '1', 'domain_field': 'mailing_domain', 'model': 'mailing_model_id'}"/>
            </form>`,
    });

    expect(".o_mass_mailing_save_filter_container").toBeVisible();
    expect(".o_mass_mailing_remove_filter").not.toBeVisible();

    await contains("div[name='mailing_domain'] input").edit("[");
    await animationFrame();

    expect(".o_mass_mailing_save_filter_container").not.toBeVisible();
    expect(".o_mass_mailing_remove_filter").not.toBeVisible();
});

test("filter widget works in edit and readonly", async () => {
    Partner._fields.name.searchable = true;

    MailingFilter._records = [
        {
            id: 1,
            name: "Azure Partner Only",
            mailing_domain: "[['name','=', 'Azure Interior']]",
            mailing_model_id: 2,
        },
    ];

    Mailing._fields.state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["running", "Running"],
        ],
    });

    Mailing._records.push({
        id: 3,
        display_name: "Partner Event promotion",
        subject: "Early bird discount for Partners!",
        mailing_model_id: 2,
        mailing_model_name: "partner",
        mailing_filter_count: 1,
        mailing_filter_domain: "[['name','=', 'Azure Interior']]",
        mailing_filter_id: 1,
        mailing_domain: "[['name','=', 'Azure Interior']]",
        state: "draft",
    });

    Mailing._onChanges = {
        mailing_filter_id(record) {
            record.mailing_domain = MockServer.env["mailing.filter"].filter(
                (r) => r.id === record.mailing_filter_id
            )[0].mailing_domain;
        },
    };

    await mountView({
        type: "form",
        resModel: "mailing.mailing",
        resId: 3,
        arch: `<form>
                <field name="display_name"/>
                <field name="subject"/>
                <field name="mailing_model_name" invisible="1"/>
                <field name="mailing_model_id" readonly="state != 'draft'"/>
                <field name="mailing_filter_count" />
                <field name="mailing_filter_id" widget="mailing_filter" options="{'no_create': '1', 'no_open': '1', 'domain_field': 'mailing_domain', 'model': 'mailing_model_id'}"/>
                <field name="state" widget="statusbar" options="{'clickable' : '1'}"/>
                <group>
                    <field name="mailing_domain" widget="domain" options="{'model': 'mailing_model_name'}"/>
                </group>
            </form>`,
    });

    expect("div[name='mailing_model_id']").not.toHaveClass("o_readonly_modifier");
    expect(".o_mass_mailing_save_filter_container").not.toHaveClass("d-none");
    await contains("button[data-value='running']").click();
    await animationFrame();
    expect("div[name='mailing_model_id']").toHaveClass("o_readonly_modifier");
    expect(".o_mass_mailing_save_filter_container").not.toHaveClass("d-none");
});
