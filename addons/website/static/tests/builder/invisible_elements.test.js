import { InvisibleElementsPanel } from "@html_builder/sidebar/invisible_elements_panel";
import { getSnippetStructure, waitForEndOfOperation } from "@html_builder/../tests/helpers";
import { unformat } from "@html_editor/../tests/_helpers/format";
import { describe, expect, test } from "@odoo/hoot";
import { click, queryAllTexts, queryFirst, queryOne, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    addOption,
    addDropZoneSelector,
    defineWebsiteModels,
    invisibleEl,
    setupWebsiteBuilder,
    waitForSnippetDialog,
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

describe("drop invisible elements", () => {
    addDropZoneSelector({ selector: "*", dropNear: "section" });
    const snippetMobileInvisible = `
        <section class="s_mobile_test o_snippet_mobile_invisible d-none d-lg-block" data-snippet="s_mobile_test" data-name="Test mobile">
            <p>Hello Desktop</p>
        </section>`;
    const snippetDesktopInvisible = `
        <section class="s_desktop_test o_snippet_desktop_invisible d-lg-none" data-snippet="s_desktop_test" data-name="Test desktop">
            <p>Hello Mobile</p>
        </section>`;
    const snippetInnerDesktopInvisible = `
        <section class="s_desktop_test" data-snippet="s_desktop_test" data-name="Test desktop">
            <p>Hello All</p>
            <section class="o_snippet_desktop_invisible d-lg-none">
                <p>Hello Mobile</p>
            </section>
        </section>`;
    const snippetConditionalInvisible = `
        <section class="s_conditional_test o_conditional_hidden" data-visibility="conditional" data-snippet="s_conditional_test" data-name="Test conditional">
            <p>Hello All</p>
            <section class="o_conditional_hidden" data-visibility="conditional" data-snippet="s_inner_conditional_test">
                <p>Hello Sometimes</p>
            </section>
        </section>`;
    const snippetDesktopAndConditionalInvisible = `
        <section class="s_desktop_and_conditional_test o_snippet_desktop_invisible d-lg-none o_conditional_hidden" data-visibility="conditional" data-snippet="s_desktop_and_conditional_test" data-name="Test desktop and conditional">
            <p>Hello Mobile Sometimes</p>
        </section>`;

    function getSnippetInfos(snippet) {
        return {
            snippet_groups: [
                '<div name="A" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
                '<div name="Custom" data-oe-snippet-id="123" data-o-snippet-group="custom"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: [
                getSnippetStructure({
                    name: "Test",
                    groupName: "a",
                    content: unformat(snippet),
                }),
            ],
            snippet_custom: [
                getSnippetStructure({
                    name: "Custom Test",
                    groupName: "custom",
                    content: unformat(snippet),
                }),
            ],
        };
    }

    describe("snippets shown with invisible elements in snippet dialog", () => {
        test("elements with o_conditional_hidden are visible", async () => {
            await setupWebsiteBuilder(`<section>test</section>`, {
                snippets: getSnippetInfos(snippetConditionalInvisible),
            });
            await contains(
                ".o-snippets-menu #snippet_groups div[data-snippet-group=a] .o_snippet_thumbnail .o_snippet_thumbnail_area"
            ).click();
            await waitForSnippetDialog();
            expect(
                ".o_add_snippet_dialog :iframe .s_conditional_test p:contains(Sometimes)"
            ).toBeVisible();
        });

        test("snippets which are desktop invisible are visible", async () => {
            await setupWebsiteBuilder(`<section>test</section>`, {
                snippets: getSnippetInfos(snippetDesktopInvisible),
            });
            await contains(
                ".o-snippets-menu #snippet_groups div[data-snippet-group=a] .o_snippet_thumbnail .o_snippet_thumbnail_area"
            ).click();
            await waitForSnippetDialog();
            expect(
                ".o_add_snippet_dialog :iframe .s_desktop_test p:contains(Hello Mobile)"
            ).toBeVisible();
        });

        test("elements which are desktop invisible inside a snippet are invisible", async () => {
            await setupWebsiteBuilder(`<section>test</section>`, {
                snippets: getSnippetInfos(snippetInnerDesktopInvisible),
            });
            await contains(
                ".o-snippets-menu #snippet_groups div[data-snippet-group=a] .o_snippet_thumbnail .o_snippet_thumbnail_area"
            ).click();
            await waitForSnippetDialog();
            expect(
                ".o_add_snippet_dialog :iframe .s_desktop_test p:contains(Mobile)"
            ).not.toBeVisible();
        });
    });

    describe("invisible snippets have an indicator in snippet dialog telling they are invisible", () => {
        test("mobile invisible snippet", async () => {
            await setupWebsiteBuilder(`<section>test</section>`, {
                snippets: getSnippetInfos(snippetMobileInvisible),
            });
            await contains(
                ".o-snippets-menu #snippet_groups div[data-snippet-group=custom] .o_snippet_thumbnail .o_snippet_thumbnail_area"
            ).click();
            await waitForSnippetDialog();
            await waitFor(".o_add_snippet_dialog :iframe .o_custom_snippet_edit");
            expect(
                ".o_add_snippet_dialog :iframe .o_custom_snippet_edit .o_prefix_mobile_invisible"
            ).toHaveCount(1);
        });

        test("desktop invisible snippet", async () => {
            await setupWebsiteBuilder(`<section>test</section>`, {
                snippets: getSnippetInfos(snippetDesktopInvisible),
            });
            await contains(
                ".o-snippets-menu #snippet_groups div[data-snippet-group=custom] .o_snippet_thumbnail .o_snippet_thumbnail_area"
            ).click();
            await waitForSnippetDialog();
            await waitFor(".o_add_snippet_dialog :iframe .o_custom_snippet_edit");
            expect(
                ".o_add_snippet_dialog :iframe .o_custom_snippet_edit .o_prefix_desktop_invisible"
            ).toHaveCount(1);
        });

        test("conditionally visible snippet", async () => {
            await setupWebsiteBuilder(`<section>test</section>`, {
                snippets: getSnippetInfos(snippetConditionalInvisible),
            });
            await contains(
                ".o-snippets-menu #snippet_groups div[data-snippet-group=custom] .o_snippet_thumbnail .o_snippet_thumbnail_area"
            ).click();
            await waitForSnippetDialog();
            await waitFor(".o_add_snippet_dialog :iframe .o_custom_snippet_edit");
            expect(
                ".o_add_snippet_dialog :iframe .o_custom_snippet_edit .o_prefix_conditional"
            ).toHaveCount(1);
        });

        test("both desktop invisible and conditionally visible snippet", async () => {
            await setupWebsiteBuilder(`<section>test</section>`, {
                snippets: getSnippetInfos(snippetDesktopAndConditionalInvisible),
            });
            await contains(
                ".o-snippets-menu #snippet_groups div[data-snippet-group=custom] .o_snippet_thumbnail .o_snippet_thumbnail_area"
            ).click();
            await waitForSnippetDialog();
            await waitFor(".o_add_snippet_dialog :iframe .o_custom_snippet_edit");
            expect(
                ".o_add_snippet_dialog :iframe .o_custom_snippet_edit .o_prefix_conditional"
            ).toHaveCount(1);
            expect(
                ".o_add_snippet_dialog :iframe .o_custom_snippet_edit .o_prefix_desktop_invisible"
            ).toHaveCount(1);
        });
    });
});
