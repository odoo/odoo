import { expect, test } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { insertText, undo } from "@html_editor/../tests/_helpers/user_actions";
import { setSelection } from "@html_editor/../tests/_helpers/selection";

defineWebsiteModels();

const websiteContent = `
        <section>
            <div class="container">
                <div class="row">
                    <div class="col-lg-3">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `;

test("click on 'Show/hide on desktop'", async () => {
    await setupWebsiteBuilder(websiteContent);
    await contains(":iframe .col-lg-3").click();

    await contains("button[data-action-id='toggleDeviceVisibility']").click();
    expect(".options-container").not.toHaveCount();

    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    await contains("button[data-action-id='toggleDeviceVisibility']").click();
    expect(".o_we_invisible_el_panel").not.toHaveCount();
});

test("show/hide a section", async () => {
    await setupWebsiteBuilderWithSnippet("s_text_image");
    await contains(":iframe section").click();
    await contains(
        "[data-action-id='toggleDeviceVisibility'][data-action-param='no_desktop']"
    ).click();
    expect(":iframe section").toHaveClass("d-lg-none o_snippet_desktop_invisible");
    expect(":iframe section").not.toHaveClass("o_snippet_override_invisible");
    expect(":iframe section").toHaveAttribute("data-invisible", "1");
    await contains(".o_we_invisible_entry").click();
    expect(":iframe section").toHaveClass(
        "d-lg-none o_snippet_desktop_invisible o_snippet_override_invisible"
    );
    expect(":iframe section").not.toHaveAttribute("data-invisible");
});

test("click on 'Hide on Mobile' then on 'Hide on desktop'", async () => {
    await setupWebsiteBuilder(websiteContent);
    await contains(":iframe .col-lg-3").click();
    await animationFrame();
    await contains("button[data-action-id='toggleDeviceVisibility']:last").click();
    expect("button[data-action-id='toggleDeviceVisibility']:first").not.toHaveClass("active");
    expect("button[data-action-id='toggleDeviceVisibility']:last").toHaveClass("active");

    await contains("button[data-action-id='toggleDeviceVisibility']").click();
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    await animationFrame();
    expect("button[data-action-id='toggleDeviceVisibility']:first").toHaveClass("active");
    expect("button[data-action-id='toggleDeviceVisibility']:last").not.toHaveClass("active");
});

test("check invisible element after save", async () => {
    const resultSave = [];
    onRpc("ir.ui.view", "save", ({ args }) => {
        resultSave.push(args[1]);
        return true;
    });
    await setupWebsiteBuilder(websiteContent);
    await contains(":iframe .col-lg-3").click();

    await contains(
        "[data-container-title='Column'] button[data-action-id='toggleDeviceVisibility']"
    ).click();
    expect(":iframe .row").toHaveInnerHTML(`
        <div class="col-lg-3 o_colored_level o_draggable d-lg-none o_snippet_desktop_invisible" data-invisible="1">
            <p>TEST</p>
        </div>
    `);
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect(resultSave[0]).toBe(
        `<div id="wrap" class="oe_structure oe_empty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch">
        <section class="o_colored_level">
            <div class="container">
                <div class="row">
                    <div class="col-lg-3 o_colored_level d-lg-none o_snippet_desktop_invisible" data-invisible="1">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    </div>`
    );
});

test("click on 'Show/hide on mobile' in mobile view", async () => {
    await setupWebsiteBuilder(websiteContent);
    await contains(":iframe .col-lg-3").click();
    await contains("button[data-action='mobile']").click();

    await contains("button[data-action-id='toggleDeviceVisibility']:last").click();
    expect(".o-snippets-tabs button:contains('Blocks')").toHaveClass("active");
    expect(":iframe .col-lg-3[data-invisible='1']").toHaveClass("o_snippet_mobile_invisible");
});

test("click on 'Show/hide on mobile' in desktop view", async () => {
    await setupWebsiteBuilder(websiteContent);
    await contains(":iframe .col-lg-3").click();

    await contains("button[data-action-id='toggleDeviceVisibility']:last").click();
    expect("button[data-action-id='toggleDeviceVisibility']:last").toHaveClass("active");
    expect(":iframe .col-lg-3").toHaveClass("o_snippet_mobile_invisible");
});

test("click on 'Show/hide on desktop' in mobile view", async () => {
    await setupWebsiteBuilder(websiteContent);
    await contains(":iframe .col-lg-3").click();
    await contains("button[data-action='mobile']").click();

    await contains(
        "[data-container-title='Column']  button[data-action-id='toggleDeviceVisibility']"
    ).click();
    expect(
        "[data-container-title='Column']  button[data-action-id='toggleDeviceVisibility']:first"
    ).toHaveClass("active");
    expect(":iframe .col-lg-3").toHaveClass("o_snippet_desktop_invisible");
});

test("hide on mobile and toggle mobile view", async () => {
    await setupWebsiteBuilder(websiteContent);
    await contains(":iframe .col-lg-3").click();

    await contains("button[data-action-id='toggleDeviceVisibility']:last").click();
    await contains("button[data-action='mobile']").click();
    expect(":iframe .col-lg-3").not.toHaveClass("o_snippet_override_invisible");
    expect(queryOne(".o_we_invisible_el_panel .o_we_invisible_entry i")).toHaveClass(
        "fa-eye-slash"
    );

    await contains("button[data-action='mobile']").click();
    expect(".o_we_invisible_el_panel").not.toHaveCount();
});

test("Hide element conditionally", async () => {
    await setupWebsiteBuilder(websiteContent);

    await contains(":iframe section").click();
    await contains("[data-label='Visibility'] button.dropdown").click();
    await contains("div[data-action-id='forceVisible']:contains(Conditionally)").click();
    expect(":iframe section").toHaveClass("o_snippet_invisible");
    expect(".o_we_invisible_el_panel .o_we_invisible_entry").toHaveCount(1);
    expect(".o_we_invisible_el_panel .o_we_invisible_entry i").toHaveClass("fa-eye");

    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect(":iframe section.o_snippet_invisible").toHaveClass("o_conditional_hidden");
    expect(":iframe section").toHaveAttribute("data-invisible", "1");
    expect(".o_we_invisible_el_panel .o_we_invisible_entry i").toHaveClass("fa-eye-slash");

    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect(":iframe section.o_snippet_invisible").not.toHaveClass("o_conditional_hidden");
    expect(":iframe section").not.toHaveAttribute("data-invisible");

    await contains("[data-label='Visibility'] button.dropdown").click();
    await contains("div[data-action-id='forceVisible']").click();
    expect(":iframe section").not.toHaveClass("o_snippet_invisible");
});

test("Show conditionally hidden elements should not be tracked in history", async () => {
    const { getEditor } = await setupWebsiteBuilder(websiteContent);

    await contains(":iframe section").click();
    await contains("[data-label='Visibility'] button.dropdown").click();
    await contains("div[data-action-id='forceVisible']:contains(Conditionally)").click();
    expect(":iframe section").toHaveClass("o_snippet_invisible");
    expect(".o_we_invisible_el_panel .o_we_invisible_entry").toHaveCount(1);
    expect(".o_we_invisible_el_panel .o_we_invisible_entry i").toHaveClass("fa-eye");

    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect(":iframe section.o_snippet_invisible").toHaveClass("o_conditional_hidden");
    expect(":iframe section").toHaveAttribute("data-invisible", "1");
    expect(".o_we_invisible_el_panel .o_we_invisible_entry i").toHaveClass("fa-eye-slash");

    setSelection({ anchorNode: queryOne(":iframe p:not([data-selection-placeholder])"), anchorOffset: 1 });
    await insertText(getEditor(), "x"); // something to undo
    undo(getEditor());
    expect(":iframe section.o_snippet_invisible").toHaveClass("o_conditional_hidden");
    expect(":iframe section").toHaveAttribute("data-invisible", "1");
    expect(".o_we_invisible_el_panel .o_we_invisible_entry i").toHaveClass("fa-eye-slash");
});
