import { expect, test, describe, beforeEach, getFixture } from "@odoo/hoot";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    clickSave,
    patchWithCleanup,
    contains,
    getPagerValue,
    getPagerLimit,
} from "@web/../tests/web_test_helpers";
import { click, queryAny, queryOne, waitFor } from "@odoo/hoot-dom";
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
    state = fields.Selection({
        string: "Status",
        default: "draft",
        selection: [
            ["draft", "Draft"],
            ["in_queue", "In Queue"],
            ["sending", "Sending"],
            ["done", "Sent"],
        ],
    });

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
        {
            id: 2,
            display_name: "Sent Belgian Event promotion",
            mailing_model_id: 1,
            body_arch: `
                <div data_name="Mailing" class="o_layout oe_unremovable oe_unmovable o_empty_theme">
                    <div class="container o_mail_wrapper o_mail_regular oe_unremovable">
                        <div class="row">
                            <div class="col o_mail_no_options o_mail_wrapper_td bg-white oe_structure o_editable oe_empty" data-editor-message-default="true" data-editor-message="DRAG BUILDING BLOCKS HERE" contenteditable="true">
                                This element <t t-out="'should be inline'"/>
                            </div>
                        </div>
                    </div>
                </div>
            `,
            state: "done",
        },
        {
            id: 3,
            display_name: "Readonly",
            mailing_model_id: 1,
            body_arch: `
                <div data_name="Mailing" class="o_layout oe_unremovable oe_unmovable o_default_theme">
                    <div class="container o_mail_wrapper o_mail_regular oe_unremovable">
                        <div class="row mw-100 mx-0">
                            <div class="col o_mail_no_options o_mail_wrapper_td bg-white oe_structure">
                                <section class="s_text_block o_mail_snippet_general" data-snippet="s_text_block">
                                    <div class="container">
                                        <p>Readonly</p>
                                    </div>
                                </section>
                            </div>
                        </div>
                    </div>
                </div>
            `,
            state: "done",
        },
        {
            id: 4,
            display_name: "Basic",
            mailing_model_id: 1,
            body_arch: `
                <div data_name="Mailing" class="o_layout oe_unremovable oe_unmovable o_basic_theme">
                    <div class="oe_structure">
                        <div class="o_mail_no_options">
                            <p>Basic</p>
                        </div>
                    </div>
                </div>
            `,
        },
        {
            id: 5,
            display_name: "Builder",
            mailing_model_id: 1,
            body_arch: `
                <div data_name="Mailing" class="o_layout oe_unremovable oe_unmovable o_empty_theme">
                    <div class="container o_mail_wrapper o_mail_regular oe_unremovable">
                        <div class="row mw-100 mx-0">
                            <div class="col o_mail_no_options o_mail_wrapper_td bg-white oe_structure">
                                <section class="s_text_block o_mail_snippet_general" data-snippet="s_text_block">
                                    <div class="container">
                                        <p>Builder</p>
                                    </div>
                                </section>
                            </div>
                        </div>
                    </div>
                </div>
            `,
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
    <field name="mailing_model_real" invisible="1"/>
    <field name="state" invisible="1"/>
    <field name="body_html" class="o_mail_body_inline"/>
    <field name="body_arch" class="o_mail_body_mailing" widget="mass_mailing_html"
        options="{
            'inline_field': 'body_html',
            'dynamic_placeholder': true,
            'dynamic_placeholder_model_reference_field': 'mailing_model_real'
            }" readonly="state in ('sending', 'done')"/>
</form>
`;

/**
 * @type {MassMailingHtmlField}
 */
let htmlField;
describe.current.tags("desktop");
beforeEach(() => {
    patchWithCleanup(MassMailingHtmlField.prototype, {
        setup() {
            super.setup();
            htmlField = this;
        },
    });
});
describe("field HTML", () => {
    beforeEach(() => {
        patchWithCleanup(MassMailingIframe.prototype, {
            // Css assets are not needed for these tests.
            loadIframeAssets() {
                return {
                    "mass_mailing.assets_inside_builder_iframe": {
                        toggle: () => {},
                    },
                };
            },
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
        await click(
            waitFor(
                ".o_mailing_template_preview_wrapper div[role='menuitem']:contains(Start From Scratch)"
            )
        );
        await waitFor(".o_mass_mailing_iframe_wrapper iframe:not(.d-none)");
        expect(await waitFor(":iframe .o_layout", { timeout: 3000 })).toHaveClass("o_empty_theme");
        await clickSave();
        await expect.waitForSteps(["web_save mail body"]);
    });
    test("t-out field in uneditable mode inline", async () => {
        await mountView({
            type: "form",
            resModel: "mailing.mailing",
            resId: 2,
            arch: mailViewArch,
        });
        await waitFor(".o_mass_mailing_iframe_wrapper iframe:not(.d-none)");
        const tElement = await waitFor(":iframe t", { timeout: 3000 });

        // assert that we are in readonly mode (sanity check)
        expect(":iframe .o_mass_mailing_value.o_readonly").toHaveCount(1);

        // assert that tElement style has inline attibute
        expect(tElement).toHaveAttribute("data-oe-t-inline", "true");
    });

    test("builder in modal -- owl reconciliation iframe unload", async () => {
        // Related to ad-hoc fix where in modal, some editor's popovers
        // get to be spawned before the modal in the DOM and in OWL
        // When those popovers are killed, OWL tries to reconcile its element List
        // in OverlayContainer, displaces the node that contains the iframe
        // and the editor subsequently crashes
        const base64Img =
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII=";
        onRpc("/html_editor/get_image_info", () => ({
            original: { image_src: base64Img },
        }));
        class SomeModel extends models.Model {
            _name = "some.model";
            mailing_ids = fields.One2many({ relation: "mailing.mailing" });

            _records = [
                {
                    id: 1,
                    mailing_ids: [1],
                },
            ];
        }

        Mailing._views["form"] = mailViewArch;
        defineModels([SomeModel]);
        const arch = `<form><field name="mailing_ids"> <list><field name="display_name" /></list> </field></form>`;
        await mountView({
            type: "form",
            resModel: "some.model",
            arch,
            resId: 1,
        });
        await contains(".o_data_cell").click();
        await waitFor(".o_dialog");
        await contains(".o_dialog [data-name='event']").click();
        await waitFor(".o_dialog .o_mass_mailing-builder_sidebar", { timeout: 1000 });
        await contains(".o_dialog :iframe p", { timeout: 1000 }).click();
        await waitFor(
            ".o_dialog .o_mass_mailing-builder_sidebar .options-container-header:contains(Text)"
        );
        const overlayOptionsSelect =
            ".o-main-components-container .o-overlay-container .o_overlay_options";
        await waitFor(overlayOptionsSelect + ":has(button[title='Move up'])");
        await contains(".o_dialog :iframe img").click();
        await waitFor(overlayOptionsSelect + ":not(:has(button[title='Move up']))");
    });
    test("preprocess some domain", async () => {
        await mountView({
            type: "form",
            resModel: "mailing.mailing",
            resId: 1,
            arch: mailViewArch,
        });
        await click(waitFor(".o_mailing_template_preview_wrapper [data-name='default']"));
        await waitFor(".o_mass_mailing_iframe_wrapper iframe:not(.d-none)");
        expect(await waitFor(":iframe .o_layout", { timeout: 3000 })).toHaveClass(
            "o_default_theme"
        );
        await runAllTimers();
        const section = queryAny(":iframe section");
        section.dataset.filterDomain = JSON.stringify([["id", "=", 1]]);
        htmlField.editor.shared["history"].addStep();
        await click(section);
        await waitFor(".hb-row .hb-row-label span:contains(Domain)");
        expect(queryOne(".hb-row span.fa-filter + span").textContent.toLowerCase()).toBe("id = 1");
        await clickSave();
        await waitFor("table[t-if]");
        expect(queryOne("table[t-if]")).toHaveAttribute(
            "t-if",
            'object.filtered_domain([("id", "=", 1)])'
        );
    });
    test(`Switching mailing records in the Form view properly switches between basic Editor, HtmlBuilder and readonly`, async () => {
        const fixture = getFixture();
        let htmlField;
        patchWithCleanup(MassMailingHtmlField.prototype, {
            setup() {
                super.setup();
                htmlField = this;
            },
        });
        await mountView({
            resModel: "mailing.mailing",
            type: "form",
            arch: mailViewArch,
            resIds: [3, 4, 5],
            resId: 3,
        });
        // readonly default
        expect(await waitFor(":iframe .o_layout", { timeout: 3000 })).toHaveClass(
            "o_default_theme"
        );
        expect(getPagerValue()).toEqual([1]);
        expect(getPagerLimit()).toBe(3);
        expect(htmlField.state.activeTheme).toBe("default");
        expect(fixture.querySelectorAll(".o_mass_mailing-builder_sidebar")).toHaveCount(0);
        // editable basic
        await contains(`.o_pager_next`).click();
        await waitFor(".o_mass_mailing_iframe_wrapper :iframe .o_layout.o_basic_theme", {
            timeout: 3000,
        });
        expect(getPagerValue()).toEqual([2]);
        expect(htmlField.state.activeTheme).toBe("basic");
        expect(fixture.querySelectorAll(".o_mass_mailing-builder_sidebar")).toHaveCount(0);
        // editable builder
        await contains(`.o_pager_next`).click();
        await waitFor(".o_mass_mailing_iframe_wrapper :iframe .o_layout.o_empty_theme", {
            timeout: 3000,
        });
        expect(getPagerValue()).toEqual([3]);
        expect(htmlField.state.activeTheme).toBe("empty");
        expect(fixture.querySelectorAll(".o_mass_mailing-builder_sidebar")).toHaveCount(1);
        // readonly default
        await contains(`.o_pager_next`).click();
        await waitFor(".o_mass_mailing_iframe_wrapper :iframe .o_layout.o_default_theme", {
            timeout: 3000,
        });
        expect(getPagerValue()).toEqual([1]);
        expect(htmlField.state.activeTheme).toBe("default");
        expect(fixture.querySelectorAll(".o_mass_mailing-builder_sidebar")).toHaveCount(0);
    });
});
describe("field HTML: with loaded assets", () => {
    test("Ensure style bundles loaded in the `MassMailingIframe` can be toggled On or Off", async () => {
        await mountView({
            type: "form",
            resModel: "mailing.mailing",
            resId: 1,
            arch: mailViewArch,
        });
        await click(waitFor(".o_mailing_template_preview_wrapper [data-name='default']"));
        await waitFor(".o_mass_mailing_iframe_wrapper iframe:not(.d-none)");
        const { bundleControls } = await htmlField.ensureIframeLoaded();

        expect(
            htmlField.iframeRef.el.contentDocument.head.querySelectorAll(
                '[href*="mass_mailing.assets_inside_builder_iframe"]'
            )
        ).toHaveLength(1);

        bundleControls["mass_mailing.assets_inside_builder_iframe"].toggle(false);
        expect(
            htmlField.iframeRef.el.contentDocument.head.querySelectorAll(
                '[href*="mass_mailing.assets_inside_builder_iframe"]'
            )
        ).toHaveLength(0);

        bundleControls["mass_mailing.assets_inside_builder_iframe"].toggle(true);
        expect(
            htmlField.iframeRef.el.contentDocument.head.querySelectorAll(
                '[href*="mass_mailing.assets_inside_builder_iframe"]'
            )
        ).toHaveLength(1);
    });
});
