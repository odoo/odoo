import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "../website_helpers";

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
    expect(".options-container").not.toBeDisplayed();

    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    await contains("button[data-action-id='toggleDeviceVisibility']").click();
    expect(".o_we_invisible_el_panel").not.toBeDisplayed();
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
    await contains("button[data-action-id='toggleDeviceVisibility']:last").click();
    expect("button[data-action-id='toggleDeviceVisibility']:first").not.toHaveClass("active");
    expect("button[data-action-id='toggleDeviceVisibility']:last").toHaveClass("active");

    await contains("button[data-action-id='toggleDeviceVisibility']").click();
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
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
        <div class="col-lg-3 d-lg-none o_snippet_desktop_invisible" data-invisible="1">
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
                    <div class="col-lg-3 d-lg-none o_snippet_desktop_invisible" data-invisible="1">
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
    expect(".o-snippets-tabs button:contains('BLOCKS')").toHaveClass("active");
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
    expect(".o_we_invisible_el_panel").not.toBeDisplayed();
});
