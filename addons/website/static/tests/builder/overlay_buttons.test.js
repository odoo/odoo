import { undo } from "@html_editor/../tests/_helpers/user_actions";
import { Plugin } from "@html_editor/plugin";
import { setContent, setSelection } from "@html_editor/../tests/_helpers/selection";
import { expect, test } from "@odoo/hoot";
import { Deferred, queryOne, tick, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addActionOption,
    addOption,
    addPlugin,
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "./website_helpers";
import { BuilderAction } from "@html_builder/core/builder_action";

defineWebsiteModels();

test("Use the 'move arrows' overlay buttons", async () => {
    await setupWebsiteBuilder(
        `
        <section>
            <div class="container">
                <div class="row">
                    <div class="col-lg-5">
                        <p>TEST</p>
                    </div>
                    <div class="col-lg-4">
                        <p>TEST</p>
                    </div>
                    <div class="col-lg-3">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
        <section>
            <p>TEST</p>
        </section>
    `,
        { loadIframeBundles: true }
    );

    await contains(":iframe section").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".overlay .fa-angle-down").toHaveCount(1);
    expect(".overlay .fa-angle-up").toHaveCount(0);
    expect(".overlay .fa-angle-left, .overlay .fa-angle-right").toHaveCount(0);

    await contains(":iframe .col-lg-5").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".overlay .fa-angle-right").toHaveCount(1);
    expect(".overlay .fa-angle-left").toHaveCount(0);
    expect(".overlay .fa-angle-up, .overlay .fa-angle-down").toHaveCount(0);

    await contains(":iframe .col-lg-3").click();
    expect(".overlay .fa-angle-right").toHaveCount(0);
    expect(".overlay .fa-angle-left").toHaveCount(1);

    await contains(":iframe .col-lg-4").click();
    expect(".overlay .fa-angle-right").toHaveCount(1);
    expect(".overlay .fa-angle-left").toHaveCount(1);

    await contains(".overlay .fa-angle-left").click();
    expect(":iframe .col-lg-4:nth-child(1)").toHaveCount(1);
    expect(".overlay .fa-angle-right").toHaveCount(1);
    expect(".overlay .fa-angle-left").toHaveCount(0);
});

test("Full-width columns use vertical move arrows", async () => {
    await setupWebsiteBuilder(
        `
        <section>
            <div class="container">
                <div class="row">
                    <div class="col-lg-12"><p>Full width 1</p></div>
                    <div class="col-lg-12"><p>Full width 2</p></div>
                    <div class="col-lg-12"><p>Full width 3</p></div>
                </div>
            </div>
        </section>
    `,
        { loadIframeBundles: true }
    );

    await contains(":iframe .col-lg-12:nth-child(1)").click();
    expect(".overlay .fa-angle-up").toHaveCount(0);
    expect(".overlay .fa-angle-down").toHaveCount(1);
    expect(".overlay .fa-angle-left, .overlay .fa-angle-right").toHaveCount(0);

    await contains(":iframe .col-lg-12:nth-child(2)").click();
    expect(".overlay .fa-angle-up").toHaveCount(1);
    expect(".overlay .fa-angle-down").toHaveCount(1);
    expect(".overlay .fa-angle-left, .overlay .fa-angle-right").toHaveCount(0);

    await contains(":iframe .col-lg-12:nth-child(3)").click();
    expect(".overlay .fa-angle-up").toHaveCount(1);
    expect(".overlay .fa-angle-down").toHaveCount(0);
    expect(".overlay .fa-angle-left, .overlay .fa-angle-right").toHaveCount(0);
});

test("Use the 'move arrows' overlay buttons within an editable div", async () => {
    await setupWebsiteBuilder(
        `
        <div contenteditable="true">
        <section>
            <div class="container">
                <div class="row">
                    <div class="col-lg-5">
                        <p>TEST</p>
                    </div>
                    <div class="col-lg-4">
                        <p>TEST</p>
                    </div>
                    <div class="col-lg-3">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
        <section>
            <p>TEST</p>
        </section>
        </div>
    `,
        { loadIframeBundles: true }
    );

    await contains(":iframe section").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".overlay .fa-angle-down").toHaveCount(1);
    expect(".overlay .fa-angle-up").toHaveCount(0);
    expect(".overlay .fa-angle-left, .overlay .fa-angle-right").toHaveCount(0);

    await contains(":iframe .col-lg-5").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".overlay .fa-angle-right").toHaveCount(1);
    expect(".overlay .fa-angle-left").toHaveCount(0);
    expect(".overlay .fa-angle-up, .overlay .fa-angle-down").toHaveCount(0);

    await contains(":iframe .col-lg-3").click();
    expect(".overlay .fa-angle-right").toHaveCount(0);
    expect(".overlay .fa-angle-left").toHaveCount(1);

    await contains(":iframe .col-lg-4").click();
    expect(".overlay .fa-angle-right").toHaveCount(1);
    expect(".overlay .fa-angle-left").toHaveCount(1);

    await contains(".overlay .fa-angle-left").click();
    expect(":iframe .col-lg-4:nth-child(1)").toHaveCount(1);
    expect(".overlay .fa-angle-right").toHaveCount(1);
    expect(".overlay .fa-angle-left").toHaveCount(0);
});

test("Use the 'grid' overlay buttons", async () => {
    await setupWebsiteBuilder(`
        <section>
            <div class="container">
                <div class="row o_grid_mode" data-row-count="4">
                    <div class="o_grid_item g-height-4 g-col-lg-7 col-lg-7" style="grid-area: 1 / 1 / 5 / 8; z-index: 1;">
                        <p>TEST</p>
                    </div>
                    <div class="o_grid_item g-height-2 g-col-lg-5 col-lg-5" style="grid-area: 1 / 8 / 3 / 13; z-index: 2;">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `);

    await contains(":iframe .g-col-lg-5").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".overlay .o_send_back").toHaveCount(1);
    expect(".overlay .o_bring_front").toHaveCount(1);

    await contains(".overlay .o_send_back").click();
    expect(":iframe .g-col-lg-5").toHaveStyle({ zIndex: "0" });

    await contains(".overlay .o_bring_front").click();
    expect(":iframe .g-col-lg-5").toHaveStyle({ zIndex: "2" });
});

test("Refresh the overlay buttons when toggling the mobile preview", async () => {
    await setupWebsiteBuilder(
        `
        <section>
            <div class="container">
                <div class="row o_grid_mode" data-row-count="4">
                    <div class="o_grid_item g-height-4 g-col-lg-5 col-lg-5" style="grid-area: 1 / 1 / 5 / 6; z-index: 1;">
                        <p>TEST</p>
                    </div>
                    <div class="o_grid_item g-height-2 g-col-lg-4 col-lg-4" style="grid-area: 1 / 6 / 3 / 10; z-index: 2;">
                        <p>TEST</p>
                    </div>
                    <div class="o_grid_item g-height-2 g-col-lg-3 col-lg-3" style="grid-area: 1 / 10 / 3 / 13; z-index: 3;">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `,
        { loadIframeBundles: true }
    );

    await contains(":iframe .g-col-lg-4").click();
    await contains("[data-action='mobile']").click();
    expect(".overlay .o_send_back, .overlay .o_bring_front").toHaveCount(0);
    expect(".overlay .fa-angle-up").toHaveCount(1);
    expect(".overlay .fa-angle-down").toHaveCount(1);

    await contains("[data-action='mobile']").click();
    expect(".overlay .o_send_back").toHaveCount(1);
    expect(".overlay .o_bring_front").toHaveCount(1);
    expect(".overlay .fa-angle-left, .overlay .fa-angle-right").toHaveCount(0);
});

test("Use the 'remove' overlay buttons: removing a grid item", async () => {
    await setupWebsiteBuilder(`
        <section>
            <div class="container">
                <div class="row o_grid_mode" data-row-count="14">
                    <div class="o_grid_item g-height-4 g-col-lg-7 col-lg-7" style="grid-area: 1 / 1 / 5 / 8; z-index: 1;">
                        <p>TEST</p>
                    </div>
                    <div class="o_grid_item g-height-14 g-col-lg-5 col-lg-5" style="grid-area: 1 / 8 / 15 / 13; z-index: 2;">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `);

    await contains(":iframe .g-height-14").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".overlay .oe_snippet_remove").toHaveCount(1);

    // Check that the element was removed, the grid was resized and the overlay
    // is now on the other grid item (= sibling).
    await contains(".overlay .oe_snippet_remove").click();
    expect(":iframe .g-height-14").toHaveCount(0);
    expect(":iframe .row.o_grid_mode").toHaveAttribute("data-row-count", "4");
    expect(".overlay .oe_snippet_remove").toHaveCount(1);
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .o_grid_item");
});

test("Use the 'remove' overlay buttons: closes the link popover if it is open during snippet removal", async () => {
    await setupWebsiteBuilder(`
        <section>
            <div class="container">
                <div class="row o_grid_mode" data-row-count="14">
                    <div class="o_grid_item g-height-4 g-col-lg-7 col-lg-7" style="grid-area: 1 / 1 / 5 / 8; z-index: 1;">
                        <p>TEST</p>
                    </div>
                    <div class="o_grid_item g-height-14 g-col-lg-5 col-lg-5" style="grid-area: 1 / 8 / 15 / 13; z-index: 2;">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `);

    await contains(":iframe .g-height-14").click();
    const p = queryOne(":iframe .g-height-14 p");
    setSelection({ anchorNode: p, anchorOffset: 0, focusNode: p, focusOffset: 1 });
    await waitFor(".o-we-toolbar");
    await contains('.o-we-toolbar button[name="link"]').click();
    expect(".o-we-linkpopover").toHaveCount(1);
    expect(".overlay .o_overlay_options").toHaveCount(1);
    expect(".overlay .oe_snippet_remove").toHaveCount(1);

    // Check that the link popover is closed and the element has been removed.
    await contains(".overlay .oe_snippet_remove").click();
    expect(".o-we-linkpopover").toHaveCount(0);
    expect(":iframe .g-height-14").toHaveCount(0);
    expect(".overlay .oe_snippet_remove").toHaveCount(1);
});

test("Use the 'remove' overlay buttons: removing the last element will remove the parent", async () => {
    await setupWebsiteBuilder(`
        <section class="first-section">
            <div class="container">
                <div class="row">
                    <div class="col-lg-6">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
        <section class="second-section">
            <p>TEST</p>
        </section>
    `);

    await contains(":iframe .col-lg-6").click();
    expect(".overlay .oe_snippet_remove").toHaveCount(1);

    await contains(".overlay .oe_snippet_remove").click();
    expect(":iframe .col-lg-6, :iframe .first-section").toHaveCount(0);
    expect(".overlay .oe_snippet_remove").toHaveCount(1);
    // Check that the parent sibling is selected.
    expect(".oe_overlay.oe_active").toHaveRect(":iframe .second-section");
});

test("Use the 'clone' overlay buttons", async () => {
    await setupWebsiteBuilderWithSnippet("s_text_image");

    await contains(":iframe .col-lg-5").click();
    expect(".overlay .o_snippet_clone").toHaveCount(1);
    await contains(".overlay .o_snippet_clone").click();
    expect(":iframe .col-lg-5").toHaveCount(2);

    await contains(":iframe section").click();
    expect(".overlay .o_snippet_clone").toHaveCount(1);
    await contains(".overlay .o_snippet_clone").click();
    expect(":iframe section").toHaveCount(2);
    expect(":iframe .col-lg-5").toHaveCount(4);
});

test("Applying an overlay button action should wait for the actions in progress", async () => {
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            get_overlay_buttons: { getButtons: this.getOverlayButtons.bind(this) },
            has_overlay_options: { hasOption: () => true },
        };

        getOverlayButtons(target) {
            return [
                {
                    class: "test_button",
                    title: "Test",
                    handler: () => {
                        target.classList.add("overlayButton");
                    },
                },
            ];
        }
    }
    addPlugin(TestPlugin);
    const customActionDef = new Deferred();
    addActionOption({
        customAction: class extends BuilderAction {
            static id = "customAction";
            load() {
                return customActionDef;
            }
            apply({ editingElement }) {
                editingElement.classList.add("customAction");
            }
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'"/>`,
    });

    const { getEditableContent, getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">plop</div>
    `);
    const editor = getEditor();
    const editable = getEditableContent();

    await contains(":iframe .test-options-target").click();
    await contains("[data-action-id='customAction']").click();
    expect(editable).toHaveInnerHTML(`<div class="test-options-target">plop</div>`);

    await contains(":iframe .test-options-target").click();
    await contains(".overlay .test_button").click();
    expect(editable).toHaveInnerHTML(`<div class="test-options-target">plop</div>`);

    customActionDef.resolve();
    await tick();
    expect(editable).toHaveInnerHTML(
        `<div class="test-options-target customAction overlayButton">plop</div>`
    );

    undo(editor);
    expect(editable).toHaveInnerHTML(`<div class="test-options-target customAction">plop</div>`);

    undo(editor);
    expect(editable).toHaveInnerHTML(`<div class="test-options-target">plop</div>`);
});

test("The overlay buttons should only appear for elements in editable areas, unless specified otherwise", async () => {
    class PluginA extends Plugin {
        static id = "a";
        resources = {
            get_overlay_buttons: { getButtons: this.getOverlayButtons.bind(this) },
            has_overlay_options: { hasOption: () => true },
        };

        getOverlayButtons(target) {
            return [
                {
                    class: "button-a",
                    title: "Button A",
                    handler: () => {
                        target.classList.add("overlay-button-a");
                    },
                },
            ];
        }
    }
    class PluginB extends Plugin {
        static id = "b";
        resources = {
            get_overlay_buttons: {
                getButtons: this.getOverlayButtons.bind(this),
                editableOnly: false,
            },
            has_overlay_options: { hasOption: () => true, editableOnly: false },
        };

        getOverlayButtons(target) {
            return [
                {
                    class: "button-b",
                    title: "Button B",
                    handler: () => {
                        target.classList.add("overlay-button-b");
                    },
                },
            ];
        }
    }
    addPlugin(PluginA);
    addPlugin(PluginB);

    const { getEditor } = await setupWebsiteBuilder(`<div></div>`);
    const editor = getEditor();
    setContent(
        editor.editable,
        `<div class="content">
            <div class="test-not-editable">NOT IN EDITABLE</div>
        </div>
        <div class="content o_editable">
            <div class="test-editable">IN EDITABLE</div>
        </div>`
    );
    editor.shared.history.addStep();

    await contains(":iframe .test-not-editable").click();
    expect(".overlay .button-a").toHaveCount(0);
    expect(".overlay .button-b").toHaveCount(1);

    await contains(":iframe .test-editable").click();
    expect(".overlay .button-a").toHaveCount(1);
    expect(".overlay .button-b").toHaveCount(1);
});

test("An inner snippet alone in a column should not have overlay options", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner");
    // Clicking on the "Blockquote" should activate the column overlay.
    await contains(":iframe blockquote").click();
    expect(".oe_overlay").toHaveCount(3);
    expect(".oe_overlay.oe_active").toHaveCount(2);
    // Clone the block so it is not alone anymore.
    await contains(
        ".options-container[data-container-title='Blockquote'] .oe_snippet_clone"
    ).click();
    // Only the "Blockquote" should have an overlay.
    expect(".oe_overlay").toHaveCount(3);
    expect(".oe_overlay.oe_active").toHaveCount(1);
});

test("Should hide 'move up' button when previous sibling is 'o_we_no_overlay'", async () => {
    await setupWebsiteBuilder(`
        <section class="o_we_no_overlay">
            <h1>No overlay section</h1>
        </section>
        <section class="first">
            <h1>First section</h1>
        </section>
        <section class="second">
            <h1>Second section</h1>
        </section>
    `);

    await contains(":iframe .first").click();
    expect(".overlay .o_overlay_options").toHaveCount(1);

    // Can't move up since the previous sibling is excluded
    expect(".overlay .fa-angle-up").toHaveCount(0);

    // Moving down is still valid
    expect(".overlay .fa-angle-down").toHaveCount(1);
});
