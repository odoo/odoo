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
import { advanceFrame, click, queryAny, queryOne, waitFor } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { unmockedOrm } from "@web/../tests/_framework/module_set.hoot";
import { MassMailingIframe } from "../src/iframe/mass_mailing_iframe";
import { MassMailingHtmlField } from "../src/fields/html_field/mass_mailing_html_field";

class Mailing extends models.Model {
    _name = "mailing.mailing";

    display_name = fields.Char();
    subject = fields.Char();
    body_arch = fields.Html();
    body_html = fields.Html();
    mailing_model_id = fields.Many2one({ relation: "ir.model", string: "Recipients" });
    mailing_model_real = fields.Char({
        string: "Recipients Model Name (real)",
        compute: "compute_model_real",
    });
    mailing_model_name = fields.Char({ string: "Recipients Model Name" });

    compute_model_real() {
        for (const record of this) {
            record.mailing_model_real = this.env["ir.model"].browse([
                record.mailing_model_id,
            ])[0].model;
        }
    }

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
/**
 * @type {import("@html_editor/fields/html_field").HtmlField}
 */
let htmlField;
describe.current.tags("desktop");
describe("field HTML", () => {
    beforeEach(() => {
        patchWithCleanup(MassMailingIframe.prototype, {
            // Css assets are not needed for these tests.
            loadIframeAssets() {
                return {
                    "mass_mailing.assets_inside_builder_iframe": {
                        disable: () => {},
                        enable: () => {},
                    },
                };
            },
        });
        patchWithCleanup(MassMailingHtmlField.prototype, {
            setup() {
                super.setup();
                htmlField = this;
            },
        });
    });
    test("save arch and html", async () => {
        const mailViewArch = `
        <form>
            <field name="mailing_model_name" invisible="1"/>
            <field name="mailing_model_id" invisible="1"/>
            <field name="body_html" invisible="1"/>
            <field name="body_arch" class="o_mail_body_mailing" widget="mass_mailing_html"
                options="{ 'inline_field': 'body_html' }"/>
        </form>`;
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
    test("preprocess some domain", async () => {
        const mailViewArch = `
        <form>
            <field name="mailing_model_name" invisible="1"/>
            <field name="mailing_model_id" invisible="1"/>
            <field name="mailing_model_real" invisible="1"/>
            <field name="body_html" class="o_mail_body_inline"/>
            <field name="body_arch" class="o_mail_body_mailing" widget="mass_mailing_html"
                options="{ 'inline_field': 'body_html' }"/>
        </form>`;
        await mountView({
            type: "form",
            resModel: "mailing.mailing",
            resId: 1,
            arch: mailViewArch,
        });
        await click(waitFor(".o_mailing_template_preview_wrapper a[data-name='default']"));
        await waitFor(".o_mass_mailing_iframe_wrapper iframe:not(.d-none)");
        expect(await waitFor(":iframe .o_layout", { timeout: 3000 })).toHaveClass(
            "o_default_theme"
        );
        await runAllTimers();
        const section = queryAny(":iframe section");
        section.dataset.filterDomain = JSON.stringify([["id", "=", 1]]);
        htmlField.isDirty = true;
        await click(section);
        await advanceFrame();
        expect(queryOne(".hb-row span.fa-filter + span").textContent.toLowerCase()).toBe(
            "id = 1".toLowerCase()
        );
        await clickSave();
        expect(queryOne("table[data-filter-domain]")).toHaveAttribute(
            "t-if",
            'object.filtered_domain([("id", "=", 1)])'
        );
    });
});
