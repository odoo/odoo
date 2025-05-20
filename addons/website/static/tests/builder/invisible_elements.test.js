import { InvisibleElementsPanel } from "@html_builder/sidebar/invisible_elements_panel";
import { unformat } from "@html_editor/../tests/_helpers/format";
import { expect, test } from "@odoo/hoot";
import { click, queryAllTexts, queryFirst, queryOne } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    addOption,
    addDropZoneSelector,
    defineWebsiteModels,
    getSnippetStructure,
    invisibleEl,
    setupWebsiteBuilder,
    waitForSnippetDialog,
    waitForEndOfOperation,
} from "./website_helpers";

defineWebsiteModels();

test("click on invisible elements in the invisible elements tab (check eye icon)", async () => {
    await setupWebsiteBuilder(`${invisibleEl}`);
    expect(queryOne(".o_we_invisible_el_panel .o_we_invisible_entry")).toHaveText(
        "Invisible Element"
    );
    expect(queryOne(".o_we_invisible_el_panel .o_we_invisible_entry i")).toHaveClass(
        "fa-eye-slash"
    );
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect(queryOne(".o_we_invisible_el_panel .o_we_invisible_entry i")).toHaveClass("fa-eye");
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect(queryOne(".o_we_invisible_el_panel .o_we_invisible_entry i")).toHaveClass(
        "fa-eye-slash"
    );
});

test("click on invisible elements in the invisible elements tab (check sidebar tab)", async () => {
    addOption({
        selector: ".s_test",
        template: xml`<BuilderButton classAction="'my-custom-class'"/>`,
    });
    await setupWebsiteBuilder(
        '<div class="s_test d-lg-none o_snippet_desktop_invisible" data-invisible="1">a</div>'
    );
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect("button:contains('Edit')").toHaveClass("active");
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect("button:contains('Add')").toHaveClass("active");
});

test("Add an element on the invisible elements tab", async () => {
    const snippetsDescription = [
        {
            name: "Test",
            groupName: "a",
            content: unformat(
                `<div class="s_popup_test o_snippet_invisible" data-snippet="s_popup_test" data-name="Popup">
                    <div class="test_a">Hello</div>
                </div>`
            ),
        },
    ];

    addDropZoneSelector({
        selector: "*",
        dropNear: "section",
    });
    await setupWebsiteBuilder(`${invisibleEl} <section><p>Text</p></section>`, {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription.map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    await click(
        queryFirst(
            ".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area"
        )
    );
    await waitForSnippetDialog();
    await contains(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap"
    ).click();
    await waitForEndOfOperation();
    expect(".o_we_invisible_el_panel .o_we_invisible_entry:contains('Test') .fa-eye").toHaveCount(
        1
    );
    expect(
        ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Invisible Element') .fa-eye-slash"
    ).toHaveCount(1);
});

test("mobile and desktop invisible elements panel", async () => {
    await setupWebsiteBuilder(`
        <div class="o_snippet_invisible" data-name="Popup1"></div>
        <div class="o_snippet_mobile_invisible" data-name="Popup2"></div>
        <div class="o_snippet_desktop_invisible" data-name="Popup3"></div>
    `);
    expect(queryAllTexts(".o_we_invisible_el_panel .o_we_invisible_entry")).toEqual([
        "Popup1",
        "Popup3",
    ]);
    await contains("button[data-action='mobile']").click();
    expect(queryAllTexts(".o_we_invisible_el_panel .o_we_invisible_entry")).toEqual([
        "Popup1",
        "Popup2",
    ]);
});

test("mobile and desktop option container", async () => {
    await setupWebsiteBuilder(`
        <section class="o_snippet_desktop_invisible"></section>
    `);
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect(".options-container").toBeVisible();
    await contains("button[data-action='mobile']").click();
    expect(".options-container").toBeVisible();
    await contains("button[data-action='mobile']").click();
    expect(".options-container").not.toHaveCount();
});

test("desktop option undo after override", async () => {
    const builder = await setupWebsiteBuilder(`
        <section>test</section>
    `);
    await contains(":iframe section").click();
    await contains(
        "[data-action-id='toggleDeviceVisibility'][data-action-param='no_desktop']"
    ).click();
    expect(":iframe section").not.toHaveClass("o_snippet_override_invisible");
    await contains(".o_we_invisible_entry .fa-eye-slash").click();
    expect(":iframe section").toHaveClass("o_snippet_override_invisible");
    builder.getEditor().shared.history.undo();
    expect(":iframe section").not.toHaveClass("o_snippet_override_invisible");
});

test("keep the option container of a visible snippet even if there are hidden snippet on the page", async () => {
    await setupWebsiteBuilder(`
        <section id="my_el">
            <p>TEST</p>
        </section>
        <section class="o_snippet_mobile_invisible"></section>
    `);
    await contains(":iframe #my_el").click();
    expect(".options-container").toBeVisible();
    await contains("button[data-action='mobile']").click();
    expect(".options-container").toBeVisible();
});

test("invisible elements efficiency", async () => {
    patchWithCleanup(InvisibleElementsPanel.prototype, {
        updateInvisibleElementsPanel(invisibleEls) {
            if (invisibleEls.length) {
                expect.step("update invisible panel");
            }
            return super.updateInvisibleElementsPanel(...arguments);
        },
    });
    await setupWebsiteBuilder(`
        <div class="o_snippet_invisible" data-name="Popup1"></div>
        <div class="o_snippet_mobile_invisible" data-name="Popup2"></div>
        <div class="o_snippet_desktop_invisible" data-name="Popup3"></div>
    `);
    expect.verifySteps(["update invisible panel"]);
    await contains("button[data-action='mobile']").click();
    expect.verifySteps(["update invisible panel"]);
});
