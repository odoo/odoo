import { InvisibleElementsPanel } from "@html_builder/sidebar/invisible_elements_panel";
import { unformat } from "@html_editor/../tests/_helpers/format";
import { expect, test } from "@odoo/hoot";
import { click, queryAllTexts, queryFirst, queryOne, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    addOption,
    addDropZoneSelector,
    defineWebsiteModels,
    getSnippetStructure,
    invisibleEl,
    setupWebsiteBuilder,
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
    expect("button:contains('CUSTOMIZE')").toHaveClass("active");
    await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
    expect("button:contains('BLOCKS')").toHaveClass("active");
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
    await click(queryFirst(".o-snippets-menu #snippet_groups .o_snippet_thumbnail"));
    await waitFor(".o_add_snippet_dialog iframe.show.o_add_snippet_iframe", { timeout: 500 });
    await contains(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap"
    ).click();
    expect(".o_we_invisible_el_panel .o_we_invisible_entry:contains('Test') .fa-eye").toHaveCount(
        1
    );
    expect(
        ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Invisible Element') .fa-eye-slash"
    ).toHaveCount(1);
});

test("mobile and desktop invisible elements", async () => {
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

test("invisible elements efficiency", async () => {
    patchWithCleanup(InvisibleElementsPanel.prototype, {
        updateInvisibleElementsPanel() {
            expect.step("update invisible panel");
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
