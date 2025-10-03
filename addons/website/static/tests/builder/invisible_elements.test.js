import {
    addBuilderOption,
    getDragMoveHelper,
    getSnippetStructure,
    waitForEndOfOperation,
} from "@html_builder/../tests/helpers";
import { unformat } from "@html_editor/../tests/_helpers/format";
import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { before, describe, expect, test, waitFor } from "@odoo/hoot";
import { animationFrame, click, queryAllTexts, queryFirst, queryOne } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    addDropZoneSelector,
    defineWebsiteModels,
    invisibleEl,
    setupWebsiteBuilder,
    toggleMobilePreview,
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
    addBuilderOption({
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
    await toggleMobilePreview();
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
    await toggleMobilePreview();
    expect(".options-container").toBeVisible();
    await toggleMobilePreview();
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
    await toggleMobilePreview();
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
    await toggleMobilePreview();
    expect.verifySteps(["update invisible panel"]);
});

test("showing an invisible element should display the correct buttons to move it", async () => {
    await setupWebsiteBuilder(
        `
        <section>test</section>
        <section class="test-target">test</section>
        <section>test</section>
        `,
        {
            styleContent: styleDeviceInvisible,
        }
    );
    await contains(":iframe section.test-target").click();
    await waitFor(".o_overlay_options");
    expect(".o_overlay_options button.fa-angle-up").toHaveCount(1);
    expect(".o_overlay_options button.fa-angle-down").toHaveCount(1);

    await contains(
        "[data-action-id='toggleDeviceVisibility'][data-action-param='no_desktop']"
    ).click();
    await contains(".o_we_invisible_entry i.fa-eye-slash").click();

    await waitFor(".o_overlay_options");
    expect(".o_overlay_options button.fa-angle-up").toHaveCount(1);
    expect(".o_overlay_options button.fa-angle-down").toHaveCount(1);
});

describe("undo+redo edit in an hidden section", () => {
    async function setup() {
        addPlugin(TestInvisibleElementPlugin);
        const { getEditor } = await setupWebsiteBuilder(`
            <section class="s_invisible_el target-outer" data-name="Parent" style="display: none">
                <p class="target-inner">Invisible</p>
            </section>
        `);
        await contains(".o_we_invisible_entry i.fa-eye-slash").click();
        expect(":iframe .target-inner").toBeVisible();
        return getEditor();
    }
    async function checkVisibilityUndoRedo({ editor, toggles, target }) {
        expect(`:iframe ${target}`).toBeVisible();

        for (const toggle of toggles) {
            await contains(`.o_we_invisible_entry:text("${toggle}") i.fa-eye`).click();
        }
        expect(`:iframe ${target}`).not.toBeVisible();
        undo(editor);
        expect(`:iframe ${target}`).toBeVisible();

        for (const toggle of toggles) {
            await contains(`.o_we_invisible_entry:text("${toggle}") i.fa-eye`).click();
        }
        expect(`:iframe ${target}`).not.toBeVisible();
        redo(editor);
        expect(`:iframe ${target}`).toBeVisible();
    }

    test("a snippet drop", async () => {
        const editor = await setup();

        await contains("button[data-name=blocks]").click();
        const { moveTo, drop } = await contains("[data-snippet=s_inline_text] button").drag();
        await moveTo(":iframe .target-inner");
        await drop(getDragMoveHelper());
        await waitForEndOfOperation();

        await checkVisibilityUndoRedo({ editor, toggles: ["Parent"], target: ".target-inner" });
    });
    test("a change to an option whose target is invisible", async () => {
        addBuilderOption({
            selector: ".target-outer",
            template: xml`<BuilderButton className="'test-action-outer'" classAction="'test-class'"/>`,
        });
        const editor = await setup();

        await contains("button.test-action-outer").click();
        expect(":iframe .target-outer").toHaveClass("test-class");

        await checkVisibilityUndoRedo({ editor, toggles: ["Parent"], target: ".target-inner" });
    });
    test("a change to an option whose target is inside an invisible", async () => {
        addBuilderOption({
            selector: ".target-inner",
            template: xml`<BuilderButton className="'test-action-inner'" classAction="'test-class'"/>`,
        });
        const editor = await setup();

        await contains(":iframe .target-inner").click();
        await contains("button.test-action-inner").click();
        expect(":iframe .target-inner").toHaveClass("test-class");

        await checkVisibilityUndoRedo({ editor, toggles: ["Parent"], target: ".target-inner" });
    });

    test("a change to an option inside nested invisibles", async () => {
        addBuilderOption({
            selector: ".target-nested",
            template: xml`<BuilderButton className="'test-action-nested'" classAction="'test-class'"/>`,
        });
        addPlugin(TestInvisibleElementPlugin);
        const { getEditor } = await setupWebsiteBuilder(`
            <section class="s_invisible_el target-outer" data-name="Parent" style="display: none">
                <section class="s_invisible_el target-inner" data-name="Inner" style="display: none">
                    <p class="target-nested">Invisible</p>
                </section>
            </section>
        `);
        await contains(".o_we_invisible_entry:text(Parent) i.fa-eye-slash").click();
        expect(":iframe .target-nested").not.toBeVisible();
        await contains(".o_we_invisible_entry:text(Inner) i.fa-eye-slash").click();
        const editor = getEditor();

        await contains(":iframe .target-nested").click();
        await contains("button.test-action-nested").click();
        expect(":iframe .target-nested").toHaveClass("test-class");

        await checkVisibilityUndoRedo({
            editor,
            toggles: ["Inner", "Parent"],
            target: ".target-nested",
        });
    });
});

test("set section desktop invisible then undo redo should hide the section and show a closed eye", async () => {
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
    expect(":iframe section").not.toBeVisible();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye-slash");
});

test("set section desktop invisible then show then set desktop visible then undo should show the section and show an opened eye", async () => {
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

test("elements with visibility=conditional are saved with o_conditional_hidden", async () => {
    onRpc("ir.ui.view", "save", ({ args }) => {
        expect(args[1]).toMatch(/o_conditional_hidden/);
        expect.step("save");
        return true;
    });
    await setupWebsiteBuilder(`<section>test</section>`, {
        styleContent: styleConditionalInvisible,
    });
    await contains(":iframe section").click();
    await contains("[data-label='Visibility'] button.dropdown").click();
    await contains("div.dropdown-item:contains(Conditionally)").click();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
    expect(":iframe section").toBeVisible();
    expect(":iframe section").not.toHaveClass("o_conditional_hidden");

    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect.verifySteps(["save"]);
});

test("hidden conditionally invisible elements are shown when entering the builder", async () => {
    const builder = await setupWebsiteBuilder(
        `<section
            data-visibility="conditional"
            data-visibility-value-utm-medium="[{&quot;id&quot;:4,&quot;display_name&quot;:&quot;Email&quot;,&quot;name&quot;:&quot;Email&quot;}]"
            data-visibility-selectors="html:not([data-utm-medium=&quot;Email&quot;]) body:not(.editor_enable) [data-visibility-id=&quot;utm-medium_o_4&quot;]"
            data-visibility-id="utm-medium_o_4"
        >
            test
        </section>`,
        {
            styleContent: `html:not([data-utm-medium="Email"]) body:not(.editor_enable) [data-visibility-id="utm-medium_o_4"] {
                display: none !important;
            }`,
            openEditor: false,
        }
    );
    expect(":iframe section[data-visibility=conditional]").not.toBeVisible();
    await builder.openBuilderSidebar();
    expect(":iframe section[data-visibility=conditional]").toBeVisible();
    expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
});

describe("drop invisible elements", () => {
    before(() => addDropZoneSelector({ selector: "*", dropNear: "section" }));
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
    async function dropFirstSnippet() {
        await contains(
            ".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area"
        ).click();
        await waitForSnippetDialog();
        await contains(
            ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap"
        ).click();
        await waitForEndOfOperation();
    }

    describe("show invisible snippets on drop", () => {
        test("snippet which is desktop invisible should be shown on drop", async () => {
            await setupWebsiteBuilder(`<section>test</section>`, {
                styleContent: styleDeviceInvisible,
                snippets: getSnippetInfos(snippetDesktopInvisible),
            });
            await dropFirstSnippet();
            expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
            expect(":iframe .s_desktop_test").toBeVisible();
            expect(":iframe .s_desktop_test").toHaveClass("o_snippet_override_invisible");
        });
        test("element which is desktop invisible in snippet should not be shown on drop", async () => {
            await setupWebsiteBuilder(`<section>test</section>`, {
                styleContent: styleDeviceInvisible,
                snippets: getSnippetInfos(snippetInnerDesktopInvisible),
            });
            await dropFirstSnippet();
            expect(".o_we_invisible_entry i").toHaveClass("fa-eye-slash");
            expect(":iframe .s_desktop_test").toBeVisible();
            expect(":iframe .s_desktop_test > section").not.toBeVisible();
        });
        test("elements which is conditional invisible should be shown on drop", async () => {
            await setupWebsiteBuilder(`<section>test</section>`, {
                styleContent: styleDeviceInvisible,
                snippets: getSnippetInfos(snippetConditionalInvisible),
            });
            await dropFirstSnippet();
            expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
            expect(":iframe .s_conditional_test").toBeVisible();
            expect(":iframe .s_conditional_test").not.toHaveClass("o_conditional_hidden");
            expect(":iframe .s_conditional_test").toHaveAttribute("data-visibility", "conditional");
            expect(":iframe .s_conditional_test > section").toBeVisible();
            expect(":iframe .s_conditional_test > section").not.toHaveClass("o_conditional_hidden");
            expect(":iframe .s_conditional_test > section").toHaveAttribute(
                "data-visibility",
                "conditional"
            );
        });
    });

    describe("change visibility then undo and redo", () => {
        test("snippet which is desktop invisible should be shown on redo of drop", async () => {
            const { getEditor } = await setupWebsiteBuilder(`<section>test</section>`, {
                styleContent: styleDeviceInvisible,
                snippets: getSnippetInfos(snippetDesktopInvisible),
            });
            await dropFirstSnippet();
            await contains(".o_we_invisible_entry i.fa-eye").click();
            expect(".o_we_invisible_entry i").toHaveClass("fa-eye-slash");
            expect(":iframe .s_desktop_test").not.toBeVisible();
            expect(":iframe .s_desktop_test").not.toHaveClass("o_snippet_override_invisible");
            undo(getEditor());
            redo(getEditor());
            await animationFrame();
            expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
            expect(":iframe .s_desktop_test").toBeVisible();
            expect(":iframe .s_desktop_test").toHaveClass("o_snippet_override_invisible");
        });
        test("snippet which is conditional invisible should be shown on redo of drop", async () => {
            const { getEditor } = await setupWebsiteBuilder(`<section>test</section>`, {
                styleContent: styleConditionalInvisible,
                snippets: getSnippetInfos(snippetConditionalInvisible),
            });
            await dropFirstSnippet();
            await contains(".o_we_invisible_entry.o_we_invisible_root_parent i.fa-eye").click();
            expect(":iframe .s_conditional_test").not.toBeVisible();
            expect(":iframe .s_conditional_test").toHaveClass("o_conditional_hidden");
            expect(".o_we_invisible_entry i").toHaveClass("fa-eye-slash");
            undo(getEditor());
            redo(getEditor());
            await animationFrame();
            expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
            expect(":iframe .s_conditional_test").toBeVisible();
            expect(":iframe .s_conditional_test").not.toHaveClass("o_conditional_hidden");
            expect(":iframe .s_conditional_test > section").toBeVisible();
            expect(":iframe .s_conditional_test > section").not.toHaveClass("o_conditional_hidden");
        });
        test("snippet which is conditional invisible should be shown on redo of drop in different device preview", async () => {
            const { getEditor } = await setupWebsiteBuilder(`<section>test</section>`, {
                styleContent: styleDeviceInvisible,
                snippets: getSnippetInfos(snippetDesktopInvisible),
            });
            await contains("button[data-action=mobile]").click();
            await dropFirstSnippet();
            await contains("button[data-action=mobile]").click();
            await animationFrame();
            expect(".o_we_invisible_entry i").toHaveClass("fa-eye-slash");
            expect(":iframe .s_desktop_test").not.toBeVisible();
            expect(":iframe .s_desktop_test").not.toHaveClass("o_snippet_override_invisible");
            undo(getEditor());
            redo(getEditor());
            await animationFrame();
            expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
            expect(":iframe .s_desktop_test").toBeVisible();
            expect(":iframe .s_desktop_test").toHaveClass("o_snippet_override_invisible");
        });
    });

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

describe("clone invisible elements", () => {
    test("snippet which is desktop invisible should be shown after clone", async () => {
        await setupWebsiteBuilder(
            `<section class="s_desktop_test o_snippet_desktop_invisible d-lg-none o_snippet_override_invisible">test</section>`,
            { styleContent: styleDeviceInvisible }
        );
        await contains(":iframe section").click();
        await contains("button.oe_snippet_clone").click();
        await animationFrame();
        expect(".o_we_invisible_entry i").toHaveCount(2);
        expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
        expect(":iframe .s_desktop_test").toBeVisible();
        expect(":iframe .s_desktop_test").toHaveClass("o_snippet_override_invisible");
    });
    test("element which is desktop invisible inside a snippet should not be shown after clone", async () => {
        await setupWebsiteBuilder(
            `<section>Hello <section class="s_desktop_test o_snippet_desktop_invisible d-lg-none o_snippet_override_invisible">test</section></section>`,
            { styleContent: styleDeviceInvisible }
        );
        await contains(":iframe section").click();
        await contains("button.oe_snippet_clone").click();
        await animationFrame();
        expect(".o_we_invisible_entry i").toHaveCount(2);
        expect(".o_we_invisible_entry:first i").toHaveClass("fa-eye");
        expect(".o_we_invisible_entry:last i").toHaveClass("fa-eye-slash");
        expect(":iframe .s_desktop_test:first").toBeVisible();
        expect(":iframe .s_desktop_test:last").not.toBeVisible();
    });
});

describe("preview invisible options", () => {
    test("does not add the invisible element in the panel", async () => {
        await setupWebsiteBuilder(`<section>test</section>`, {
            styleContent: styleDeviceInvisible,
        });
        await contains(":iframe section").click();
        await contains("button[data-action-param=no_desktop]").hover();
        await animationFrame();
        expect(":iframe section").not.toBeVisible();
        expect(":iframe section").toHaveClass("o_snippet_desktop_invisible");
        expect(".o_we_invisible_entry i").toHaveCount(0);
    });
    test("does not remove the invisible element in the panel", async () => {
        await setupWebsiteBuilder(`<section>test</section>`, {
            styleContent: styleDeviceInvisible,
        });
        await contains(":iframe section").click();
        await contains("button[data-action-param=no_desktop]").click();
        await contains(".o_we_invisible_entry i.fa-eye-slash").click();
        await contains("button[data-action-param=no_desktop]").hover();
        await animationFrame();
        expect(":iframe section").toBeVisible();
        expect(":iframe section").not.toHaveClass("o_snippet_desktop_invisible");
        expect(".o_we_invisible_entry i").toHaveClass("fa-eye");
    });
    test("does not remove the override class after the preview", async () => {
        await setupWebsiteBuilder(`<section>test</section>`, {
            styleContent: styleDeviceInvisible,
        });
        await contains(":iframe section").click();
        await contains("button[data-action-param=no_desktop]").click();
        await contains(".o_we_invisible_entry i.fa-eye-slash").click();
        expect(":iframe section").toHaveClass("o_snippet_override_invisible");
        await contains("button[data-action-param=no_desktop]").hover();
        await animationFrame();
        expect(":iframe section").toBeVisible();
        expect(":iframe section").not.toHaveClass("o_snippet_override_invisible");
        await contains("span:contains(Visibility)").hover();
        await animationFrame();
        expect(":iframe section").toBeVisible();
        expect(":iframe section").toHaveClass("o_snippet_override_invisible");
    });
});
