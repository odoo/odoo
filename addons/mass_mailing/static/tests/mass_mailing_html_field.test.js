import { expect, test, describe, beforeEach } from "@odoo/hoot";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    clickSave,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { click, queryOne, waitFor } from "@odoo/hoot-dom";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { unmockedOrm } from "@web/../tests/_framework/module_set.hoot";
import { MassMailingIframe } from "../src/iframe/mass_mailing_iframe";

class Mailing extends models.Model {
    _name = "mailing.mailing";

    display_name = fields.Char();
    subject = fields.Char();
    body_arch = fields.Html();
    body_html = fields.Html();
    mailing_model_id = fields.Many2one({ relation: "ir.model", string: "Recipients" });
    mailing_model_name = fields.Char({ string: "Recipients Model Name" });

    action_fetch_favorites() {
        return [];
    }

    _records = [
        {
            id: 1,
            display_name: "Belgian Event promotion",
            mailing_model_id: 1,
        },
    ];
}

class IrUiView extends models.Model {
    async render_public_asset(template, values) {
        return unmockedOrm("ir.ui.view", "render_public_asset", [template, values], {});
    }
}

class IrModel extends models.Model {
    _name = "ir.model";

    name = fields.Char();
    display_name = fields.Char();
    model = fields.Char();

    _records = [
        {
            id: 1,
            name: "Event",
            display_name: "Event",
            model: "event",
        },
    ];
}

class Event extends models.Model {
    _name = "event";

    name = fields.Char();
    country = fields.Char();

    _records = [{ id: 1, name: "BE Event", country: "be" }];
}

defineMailModels();
defineModels([IrModel, IrUiView, Mailing, Event]);

const mailViewArch = `
<form>
    <field name="mailing_model_name" invisible="1"/>
    <field name="mailing_model_id" invisible="1"/>
    <field name="body_html" invisible="1"/>
    <field name="body_arch" class="o_mail_body_mailing" widget="mass_mailing_html"
        options="{ 'inline_field': 'body_html' }"/>
</form>
`;

describe.current.tags("desktop");
describe("field HTML", () => {
    beforeEach(() => {
        patchWithCleanup(MassMailingIframe.prototype, {
            // Css assets are not needed for these tests.
            loadIframeAssets() {},
        });
    });
    test("save arch and html", async () => {
        onRpc("web_save", ({ args }) => {
            expect(args[1].body_arch).toMatch(/^<div/);
            expect(args[1].body_html).toMatch(/^<table/);
            expect.step("web_save mail body");
        });
        await mountView({
            type: "form",
            resModel: "mailing.mailing",
            resId: 1,
            arch: mailViewArch,
        });
        expect(queryOne(".o_mass_mailing_iframe_wrapper iframe")).toHaveClass("d-none");
        await click(waitFor(".o_mailing_template_preview_wrapper a:contains(Start From Scratch)"));
        await waitFor(".o_mass_mailing_iframe_wrapper iframe:not(.d-none)");
        expect(await waitFor(":iframe .o_layout", { timeout: 3000 })).toHaveClass("o_empty_theme");
        await clickSave();
        await expect.waitForSteps(["web_save mail body"]);
    });
});
