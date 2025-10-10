import { getSnippetStructure, waitForEndOfOperation } from "@html_builder/../tests/helpers";
import { unformat } from "@html_editor/../tests/_helpers/format";
import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAllTexts, queryFirst, queryOne } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    addOption,
    addDropZoneSelector,
    defineWebsiteModels,
    invisibleEl,
    setupWebsiteBuilder,
    waitForSnippetDialog,
    addPlugin,
    TestInvisibleElementPlugin,
    styleDeviceInvisible,
    styleConditionalInvisible,
} from "./website_helpers";
import { VisibilityPlugin } from "@html_builder/core/visibility_plugin";

defineWebsiteModels();

test("click on invisible elements in the invisible elements tab (check eye icon)", async () => {
    addPlugin(TestInvisibleElementPlugin);
    await setupWebsiteBuilder(invisibleEl);
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
    await setupWebsiteBuilder('<div class="s_test d-lg-none o_snippet_desktop_invisible">a</div>', {
        styleContent: styleDeviceInvisible,
    });
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect("button:contains('Style')").toHaveClass("active");
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect("button:contains('Blocks')").toHaveClass("active");
});

test("Add an element on the invisible elements tab", async () => {
    const snippetsDescription = [
        {
            name: "Test",
            groupName: "a",
            content: unformat(
                `<div class="s_popup_test s_invisible_el" data-snippet="s_popup_test" data-name="Popup">
                    <div class="test_a">Hello</div>
                </div>`
            ),
        },
    ];

    addDropZoneSelector({
        selector: "*",
        dropNear: "section",
    });
    addPlugin(TestInvisibleElementPlugin);
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
    addPlugin(TestInvisibleElementPlugin);
    await setupWebsiteBuilder(`
        <div class="s_invisible_el" data-name="Popup1"></div>
        <div class="o_snippet_mobile_invisible" data-name="Popup2"></div>
        <div class="o_snippet_desktop_invisible" data-name="Popup3"></div>
    `);
    expect(queryAllTexts(".o_we_invisible_el_panel .o_we_invisible_entry")).toEqual([
        "Popup1",
        "Popup3",
    ]);
    await contains("button[data-action='mobile']").click();
    await animationFrame();
    expect(queryAllTexts(".o_we_invisible_el_panel .o_we_invisible_entry")).toEqual([
        "Popup1",
        "Popup2",
    ]);
});

test("mobile and desktop option container", async () => {
    await setupWebsiteBuilder(
        `<section class="o_snippet_desktop_invisible d-lg-none">x</section>`,
        { styleContent: styleDeviceInvisible }
    );
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect(".options-container").toBeVisible();
    await contains("button[data-action='mobile']").click();
    expect(".options-container").toBeVisible();
    await contains("button[data-action='mobile']").click();
    await animationFrame();
    expect(".options-container").not.toHaveCount();
});

test("desktop option undo after override", async () => {
    const builder = await setupWebsiteBuilder(`<section>test</section>`, {
        styleContent: styleDeviceInvisible,
    });
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
    await setupWebsiteBuilder(
        `
        <section id="my_el">
            <p>TEST</p>
        </section>
        <section class="o_snippet_mobile_invisible d-none d-lg-block"></section>
        `,
        { styleContent: styleDeviceInvisible }
    );
    await contains(":iframe #my_el").click();
    expect(".options-container").toBeVisible();
    await contains("button[data-action='mobile']").click();
    expect(".options-container").toBeVisible();
});

test("invisible elements efficiency", async () => {
    patchWithCleanup(VisibilityPlugin.prototype, {
        getInvisibleEntries() {
            expect.step("update invisible panel");
            return super.getInvisibleEntries();
        },
    });
    await setupWebsiteBuilder(`
        <div class="s_invisible_el" data-name="Popup1"></div>
        <div class="o_snippet_mobile_invisible" data-name="Popup2"></div>
        <div class="o_snippet_desktop_invisible" data-name="Popup3"></div>
    `);
    expect.verifySteps(["update invisible panel"]);
    await contains("button[data-action='mobile']").click();
    expect.verifySteps(["update invisible panel"]);
});

test("set section desktop invisible then undo redo should show consistent eye", async () => {
    const builder = await setupWebsiteBuilder(`<section>test</section>`, {
        styleContent: styleDeviceInvisible,
    });
    await contains(":iframe section").click();
    await contains(
        "[data-action-id='toggleDeviceVisibility'][data-action-param='no_desktop']"
    ).click();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye-slash");
    expect(":iframe section").not.toBeVisible();
    undo(builder.getEditor());
    await animationFrame();
    expect(".o_we_invisible_entry").toHaveCount(0);
    expect(":iframe section").toBeVisible();
    redo(builder.getEditor());
    await animationFrame();
    expect(":iframe section").toBeVisible();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
});

test("set section desktop invisible then show then set desktop visible then undo should show consistent eye", async () => {
    const builder = await setupWebsiteBuilder(`<section>test</section>`, {
        styleContent: styleDeviceInvisible,
    });
    await contains(":iframe section").click();
    await contains(
        "[data-action-id='toggleDeviceVisibility'][data-action-param='no_desktop']"
    ).click();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye-slash");
    expect(":iframe section").not.toBeVisible();

    await contains(".o_we_invisible_entry i.fa-eye-slash").click();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
    expect(":iframe section").toBeVisible();

    await contains(
        "[data-action-id='toggleDeviceVisibility'][data-action-param='no_desktop']"
    ).click();
    expect(".o_we_invisible_entry").toHaveCount(0);
    expect(":iframe section").toBeVisible();

    undo(builder.getEditor());
    await animationFrame();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
    expect(":iframe section").toBeVisible();
});

test("set section desktop invisible then show then set conditionally invisible then hide then switch to mobile should show consistent eye", async () => {
    const builder = await setupWebsiteBuilder(`<section>test</section>`, {
        styleContent: styleDeviceInvisible + styleConditionalInvisible,
    });
    await contains(":iframe section").click();
    await contains(
        "[data-action-id='toggleDeviceVisibility'][data-action-param='no_desktop']"
    ).click();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye-slash");
    expect(":iframe section").not.toBeVisible();

    await contains(".o_we_invisible_entry i.fa-eye-slash").click();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
    expect(":iframe section").toBeVisible();

    await contains("[data-label='Visibility'] button.dropdown").click();
    await contains("div.dropdown-item:contains(Conditionally)").click();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
    expect(":iframe section").toBeVisible();

    await contains(".o_we_invisible_entry i.fa-eye").click();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye-slash");
    expect(":iframe section").not.toBeVisible();

    undo(builder.getEditor());
    await animationFrame();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
    expect(":iframe section").toBeVisible();
});
