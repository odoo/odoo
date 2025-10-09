import { beforeEach, delay, describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, queryOne, waitFor } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    addPlugin,
    defineWebsiteModels,
    insertCategorySnippet,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import {
    confirmAddSnippet,
    getDragHelper,
    waitForEndOfOperation,
    getSnippetStructure,
} from "@html_builder/../tests/helpers";
import { Plugin } from "@html_editor/plugin";
import { insertText, redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { unformat } from "@html_editor/../tests/_helpers/format";

defineWebsiteModels();

/**
 * This function is used to wait for expected bootstrap events that are
 * triggered by {@link callback}
 * @param {import("@odoo/hoot-dom").Target} target the element that should
 * receive the event
 * @param {String} type the type of event to expect
 * @param {Function} callback the callback that should trigger the event
 * @returns the result of {@link callback}
 */
async function expectToTriggerEvent(target, type, callback) {
    const el = await waitFor(target);
    const step = `event '${type}' triggered on '${target}'`;
    el.addEventListener(type, () => expect.step(step), { once: true });
    const res = await callback();
    await expect.waitForSteps([step]);
    return res;
}

describe("Popup options: empty page before edit", () => {
    let builder;
    // Note: for some reason, `before()` doesn't work.
    // Done in `beforeEach` because frontend JS takes too much time to load.
    beforeEach(async () => {
        builder = await setupWebsiteBuilder("", {
            loadIframeBundles: true,
            loadAssetsFrontendJS: true,
        });
    });
    test("dropping the popup snippet automatically displays it", async () => {
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        expect(".o_add_snippet_dialog").toHaveCount(0);
        // Check if the popup is visible.
        expect(":iframe .s_popup .modal").toHaveClass("show");
        expect(":iframe .s_popup .modal").toHaveStyle({ display: "block" });
    });

    test("dropping the popup snippet then previewing background colors keep it visible", async () => {
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        expect(".o_add_snippet_dialog").toHaveCount(0);
        expect(":iframe .s_popup .modal").toHaveStyle({ display: "block" });
        await contains(":iframe .s_popup .modal").click();
        await contains("[data-label=Backdrop] button.o_we_color_preview").click();
        await contains("button.o_color_button[data-color='#FFFF00']").hover();
        expect(":iframe .s_popup .modal").toHaveStyle({
            display: "block",
            "background-color": "rgb(255, 255, 0)",
        });
        await contains("button.o_color_button[data-color='#FF0000']").hover();
        expect(":iframe .s_popup .modal").toHaveStyle({
            display: "block",
            "background-color": "rgb(255, 0, 0)",
        });
    });

    test("saving a visible popup hides it in the saved document", async () => {
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        expect(".o_add_snippet_dialog").toHaveCount(0);
        // Check if the popup is visible.
        expect(":iframe .s_popup .modal").toHaveClass("show");
        expect(":iframe .s_popup .modal").toHaveStyle({ display: "block" });

        onRpc("ir.ui.view", "save", ({ args }) => {
            expect(args[1]).toMatch(/display: none;/);
            expect(args[1]).not.toMatch(/display: block;/);
            expect(args[1]).not.toMatch(/[ "]show[ "]/);
            expect.step("save");
            return true;
        });

        await contains("button[data-action=save]").click();
        await expect.waitForSteps(["save"]);
    });
    test("hidden popup are not taken into account when moving other snippets", async () => {
        await insertCategorySnippet({ group: "intro", snippet: "s_cover" });
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility']").click()
        );
        await insertCategorySnippet({ group: "intro", snippet: "s_cover" });
        await contains(":iframe .s_cover:last").click();
        expect(".o_overlay_options button[data-icon=keyboard_arrow_up]").toHaveCount(1);
        expect(".o_overlay_options button[data-icon=keyboard_arrow_down]").toHaveCount(0);
        await contains(".o_overlay_options button[data-icon=keyboard_arrow_up]").click();
        expect(".o_overlay_options button[data-icon=keyboard_arrow_up]").toHaveCount(0);
        expect(".o_overlay_options button[data-icon=keyboard_arrow_down]").toHaveCount(1);
    });
    test("popup are never taken into account to show arrow to move another snippet", async () => {
        await insertCategorySnippet({ group: "intro", snippet: "s_cover" });
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility']").click()
        );
        await contains(":iframe .s_cover").click();
        await contains("button:contains(Grid)").click(); // arbitrary thing to undo
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            undo(builder.getEditor())
        );
        expect(".o_overlay_options button[data-icon=keyboard_arrow_up]").toHaveCount(0);
        expect(".o_overlay_options button[data-icon=keyboard_arrow_down]").toHaveCount(0);
    });
    test("undo drop of the popup snippet remove 'overflow: hidden' (shows the scrollbar)", async () => {
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        expect(".o_add_snippet_dialog").toHaveCount(0);
        // Check if the popup is visible.
        expect(":iframe .s_popup .modal").toHaveClass("show");
        expect(":iframe .s_popup .modal").toHaveStyle({ display: "block" });
        // Check body's overflow is "hidden" (it means no scrollbar appears for it)
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });

        undo(builder.getEditor());
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
    });
    test("undo drop of the popup snippet after hiding it leaves 'overflow: hidden' (keeps the scrollbar)", async () => {
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        expect(".o_add_snippet_dialog").toHaveCount(0);
        // Check if the popup is visible.
        expect(":iframe .s_popup .modal").toHaveClass("show");
        expect(":iframe .s_popup .modal").toHaveStyle({ display: "block" });
        // Check body's overflow is "hidden" (it means no scrollbar appears for it)
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });

        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility']").click()
        );
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });

        undo(builder.getEditor());
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
    });
    test("redo drop of the popup snippet add 'overflow: hidden' (hides the scrollbar)", async () => {
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        expect(".o_add_snippet_dialog").toHaveCount(0);
        // Check if the popup is visible.
        expect(":iframe .s_popup .modal").toHaveClass("show");
        expect(":iframe .s_popup .modal").toHaveStyle({ display: "block" });
        // Check body's overflow is "hidden" (it means no scrollbar appears for it)
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
        undo(builder.getEditor());
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
        redo(builder.getEditor());
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
    });
});

test("dropping the popup snippet appends it to the end of the container", async () => {
    await setupWebsiteBuilder("<section class='first-snippet'>First snippet</section>", {
        loadIframeBundles: true,
        loadAssetsFrontendJS: true,
    });
    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [data-snippet-group='content'] .o_snippet_thumbnail"
    ).drag();
    // Drop the snippet in the first dropzone.
    await moveTo(":iframe .oe_drop_zone:first");
    await drop(getDragHelper());
    await confirmAddSnippet("s_popup");
    await waitForEndOfOperation();
    expect(":iframe #wrap.o_savable > .s_popup:last-child").toHaveCount(1);
});

const hiddenPopup = `<div class="s_popup o_draggable" data-snippet="s_popup" data-name="Popup" id="sPopup">
    <div class="modal fade s_popup_middle modal_shown" style="background-color: var(--black-50)  !important; display: none;" data-show-after="5000" data-display="afterDelay" data-consents-duration="7" data-bs-focus="false" data-bs-backdrop="false" tabindex="-1" aria-label="Popup" aria-hidden="true">
        <div class="modal-dialog d-flex">
            <div class="modal-content oe_structure">
                <button class="s_popup_close js_close_popup border-0 p-0 o_we_no_overlay o_not_editable" aria-label="Close" contenteditable="false">×</button>
                <section><p>Popup content</p></section>
            </div>
        </div>
    </div>
</div>`;

describe("Popup options: popup in page before edit", () => {
    let builder;
    // Done in `beforeEach` because frontend JS takes too much time to load.
    beforeEach(async () => {
        addPlugin(
            class extends Plugin {
                static id = "ignore_d-none_on_s_popup";
                resources = {
                    // NOTE: this plugin is here as a workaround to make the
                    // test pass, because (at the time of this commit):
                    // - the website_edit service is removed for the tests, thus
                    //   the patch that wraps interaction's functions in
                    //   `ignoreDOMMutation` is not applied
                    // - the interaction SharedPopup adds and removes `d-none`
                    //   on `.s_popup` element to track the visibility of the
                    //   modal
                    // - one of the tests here plays with the visibility of the
                    //   modal, and verifies that it did not add mutations
                    // TODO: once the service website_edit runs during the
                    // tests, this plugin should be removed
                    /**
                     * @param {import("@html_editor/core/dom_observer_plugin").NativeMutation} record
                     * @returns { boolean | undefined}
                     */
                    is_classlist_mutation_savable_predicates: (record) => {
                        if (record.target.matches?.(".s_popup") && record.className === "d-none") {
                            return false;
                        }
                    },
                };
            }
        );
        builder = await setupWebsiteBuilder(hiddenPopup, {
            loadIframeBundles: true,
            loadAssetsFrontendJS: true,
        });
    });

    test("editing a page with a popup snippet doesn't automatically display it", async () => {
        await advanceTime(5000);
        expect(":iframe .s_popup .modal").not.toBeVisible();
        expect(":iframe .s_popup").toHaveClass("d-none");
    });

    test("closing s_popup with the X button updates the invisible elements panel", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");
        expect(":iframe .s_popup .modal").toBeVisible();
        expect(":iframe .s_popup").not.toHaveClass("d-none");
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(":iframe .s_popup button.js_close_popup").click()
        );
        expect(":iframe .s_popup .modal").not.toBeVisible();
        expect(":iframe .s_popup").toHaveClass("d-none");
        await animationFrame();
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility_off");
        // Ensure that no mutations were registered in the `domObserver` plugin.
        // `commit` returns the written commit, or `false` if there were no mutations.
        expect(builder.getEditor().shared.history.commit()).toBe(false);
    });

    test("closing s_popup with other means updates the invisible elements panel", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");
        expect(":iframe .s_popup .modal").toBeVisible();
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", async () =>
            queryOne("*:has(:iframe .s_popup) iframe")
                .contentWindow.Modal.getOrCreateInstance(queryOne(":iframe .s_popup .modal"))
                .hide()
        );
        expect(":iframe .s_popup .modal").not.toBeVisible();
        await waitFor(".o_we_invisible_entry i[data-icon='visibility_off']");
        // Ensure that no mutations were registered in the history.
        // `commit` return the created step, or false if there was no mutations
        expect(builder.getEditor().shared.history.commit()).toBe(false);
    });

    test("clicking twice to show s_popup ends up consistent with the eye", async () => {
        expect(".o_we_invisible_entry i").toHaveAttribute("data-icon", "visibility_off");
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            Promise.all([
                contains(".o_we_invisible_entry").click(),
                contains(".o_we_invisible_entry").click(),
            ])
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");
        expect(":iframe .s_popup .modal").toBeVisible();
    });

    test("editing s_popup, then closing it, then undo show it again", async () => {
        const editor = builder.getEditor();
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");
        expect(":iframe .s_popup .modal").toBeVisible();
        setSelection({ anchorNode: queryOne(":iframe .s_popup section p"), anchorOffset: 0 });
        await insertText(editor, "Other content");
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(":iframe .s_popup button.js_close_popup").click()
        );
        await animationFrame();
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility_off");
        expect(":iframe .s_popup .modal").not.toBeVisible();
        expect(editor.shared.history.canUndo()).toBe(true);
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () => undo(editor));
        await builder.waitSidebarUpdated();
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");
        expect(":iframe .s_popup .modal").toBeVisible();
    });

    test("changing background color of s_popup, then closing it, then undo, then redo keep it visible", async () => {
        const editor = builder.getEditor();
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");
        expect(":iframe .s_popup .modal").toBeVisible();
        await contains("[data-label=Backdrop] button.o_we_color_preview").click();
        await contains("button.o_color_button[data-color='#FF0000']").click();
        expect(":iframe .s_popup .modal").toHaveStyle({
            display: "block",
            "background-color": "rgb(255, 0, 0)",
        });
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(":iframe .s_popup button.js_close_popup").click()
        );
        await animationFrame();
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility_off");
        expect(":iframe .s_popup .modal").not.toBeVisible();
        expect(editor.shared.history.canUndo()).toBe(true);
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () => undo(editor));
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");
        expect(":iframe .s_popup .modal").toBeVisible();
        redo(editor);
        expect(":iframe .s_popup .modal").toHaveStyle({
            display: "block",
            "background-color": "rgb(255, 0, 0)",
        });
    });

    test("undoing something on a target outside s_popup closes it", async () => {
        await insertCategorySnippet({ group: "intro", snippet: "s_cover" });
        expect(".o_add_snippet_dialog").toHaveCount(0);
        await contains(":iframe .s_cover").click();
        await contains("button:contains(Grid)").click(); // arbitrary thing to undo
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            undo(builder.getEditor())
        );
        await builder.waitSidebarUpdated();
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility_off");
    });

    test("redo of drop of another popup hides the existing one", async () => {
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        expect(".o_we_invisible_entry:first .oi").toHaveAttribute("data-icon", "visibility_off");
        expect(".o_we_invisible_entry:last .oi").toHaveAttribute("data-icon", "visibility");
        undo(builder.getEditor());
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            redo(builder.getEditor())
        );
        await animationFrame();
        expect(".o_we_invisible_entry:first .oi").toHaveAttribute("data-icon", "visibility_off");
        expect(".o_we_invisible_entry:last .oi").toHaveAttribute("data-icon", "visibility");
    });

    test("clone a popup hides the clone", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        await contains("button.oe_snippet_clone").click();
        expect(".o_we_invisible_entry:first .oi").toHaveAttribute("data-icon", "visibility");
        expect(".o_we_invisible_entry:last .oi").toHaveAttribute("data-icon", "visibility_off");
    });

    test("redo clone a popup hides the clone", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        await contains("button.oe_snippet_clone").click();
        expect(".o_we_invisible_entry:first .oi").toHaveAttribute("data-icon", "visibility");
        expect(".o_we_invisible_entry:last .oi").toHaveAttribute("data-icon", "visibility_off");

        // :not(#sPopup) to select the new popup, that will have a random id
        await expectToTriggerEvent(":iframe .s_popup:not(#sPopup) .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await animationFrame();
        expect(".o_we_invisible_entry:first .oi").toHaveAttribute("data-icon", "visibility_off");
        expect(".o_we_invisible_entry:last .oi").toHaveAttribute("data-icon", "visibility");

        undo(builder.getEditor());
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");

        redo(builder.getEditor());
        await waitFor(".o_we_invisible_entry:last [data-icon='visibility_off']");
        expect(".o_we_invisible_entry:first .oi").toHaveAttribute("data-icon", "visibility");
        expect(".o_we_invisible_entry:last .oi").toHaveAttribute("data-icon", "visibility_off");
    });

    test("delete the popup snippet remove 'overflow: hidden' (shows the scrollbar)", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        // Check body's overflow is "hidden" (it means no scrollbar appears for it)
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
        await contains(
            ".options-container[data-container-title=Popup] button[data-icon=delete]"
        ).click();
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
    });
    test("undo delete the popup snippet add 'overflow: hidden' (hides the scrollbar)", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        // Check body's overflow is "hidden" (it means no scrollbar appears for it)
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
        await contains(
            ".options-container[data-container-title=Popup] button[data-icon=delete]"
        ).click();
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
        undo(builder.getEditor());
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
    });
    test("redo delete the popup snippet remove 'overflow: hidden' (shows the scrollbar)", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        // Check body's overflow is "hidden" (it means no scrollbar appears for it)
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
        await contains(
            ".options-container[data-container-title=Popup] button[data-icon=delete]"
        ).click();
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
        undo(builder.getEditor());
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
        redo(builder.getEditor());
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
    });
    test("switch to 'Theme' tab, hide popup, switch to 'Style' tab should not have the popup as target", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        expect(".options-container[data-container-title=Popup]").toHaveCount(1);
        await contains("button[data-name=theme]").click();
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility']").click()
        );
        await contains("button[data-name=customize]").click();
        expect(".options-container[data-container-title=Popup]").toHaveCount(0);
    });

    test("emptied s_popup are removed and the options are updated correctly", async () => {
        const editor = builder.getEditor();
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");
        expect(":iframe .s_popup .modal").toBeVisible();

        await contains(":iframe section p:contains('Popup content')").click();
        await contains(
            "div[data-container-title='Block'] button[data-icon='delete'].oi-filled"
        ).click();
        expect(":iframe .s_popup").toHaveCount(0);
        expect("div[data-container-title='Block']").toHaveCount(0);

        expect(editor.shared.history.canUndo()).toBe(true);
        undo(editor);
        await animationFrame();
        expect(":iframe .s_popup").toHaveCount(1);
        expect("div[data-container-title='Block']").toHaveCount(1);

        expect(editor.shared.history.canRedo()).toBe(true);
        redo(editor);
        await animationFrame();
        expect(":iframe .s_popup").toHaveCount(0);
        expect("div[data-container-title='Block']").toHaveCount(0);

        // Undo -> Hide popup -> Redo -> Undo -> Popup expected to be visible

        expect(editor.shared.history.canUndo()).toBe(true);
        undo(editor);
        await animationFrame();
        expect(":iframe .s_popup").toHaveCount(1);
        expect("div[data-container-title='Block']").toHaveCount(1);

        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility']").click()
        );
        await animationFrame();
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility_off");

        expect(editor.shared.history.canRedo()).toBe(true);
        redo(editor);
        await animationFrame();
        expect(":iframe .s_popup").toHaveCount(0);
        expect("div[data-container-title='Block']").toHaveCount(0);

        expect(editor.shared.history.canUndo()).toBe(true);
        undo(editor);
        await animationFrame();
        expect(":iframe .s_popup").toHaveCount(1);
        expect("div[data-container-title='Block']").toHaveCount(1);
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");
    });
});

describe("Popup visibility", () => {
    test("Rapid show/hide of popup stays consistent", async () => {
        await setupWebsiteBuilder(hiddenPopup, {
            loadIframeBundles: true,
            loadAssetsFrontendJS: true,
            enableIframeTransitions: true,
        });
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility_off']").click()
        );

        await contains(".o_we_invisible_entry i[data-icon='visibility']").click();
        await contains(".o_we_invisible_entry i[data-icon='visibility_off']").click();
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(".o_we_invisible_entry i[data-icon='visibility']").click()
        );
        await animationFrame();
        expect(":iframe body").not.toHaveClass("modal-open");
        expect(".o_we_invisible_entry i").toHaveAttribute("data-icon", "visibility_off");
        expect(":iframe .s_popup").toHaveClass("d-none");
        expect(":iframe .s_popup > .modal").toHaveStyle("display: none");
        expect(":iframe .s_popup > .modal").not.toHaveClass("show");

        await contains(".o_we_invisible_entry i[data-icon='visibility_off']").click();
        await waitFor(":iframe .s_popup:not(.d-none)");

        await contains(".o_we_invisible_entry i[data-icon='visibility']").click();
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry i[data-icon='visibility_off']").click()
        );
        // Wait for everything to settle, without the delay, we may not catch a
        // potential inconsistency.
        await delay(100);
        expect(":iframe body").toHaveClass("modal-open");
        expect(".o_we_invisible_entry i").toHaveAttribute("data-icon", "visibility");
        expect(":iframe .s_popup").not.toHaveClass("d-none");
        expect(":iframe .s_popup > .modal").toHaveStyle("display: block");
        expect(":iframe .s_popup > .modal").toHaveClass("show");
    });
});

describe("Custom Popup", () => {
    const customPopupSnippet = `<div class="s_popup s_custom_snippet" data-vcss="001" data-snippet="s_popup" id="sPopup42" data-name="Custom Popup">
        <div class="modal fade s_popup_middle modal_shown show" style="display: block; background-color: var(--black-50) !important;" data-show-after="5000" data-display="afterDelay" data-consents-duration="7" data-bs-focus="false" data-bs-backdrop="false" tabindex="-1" aria-label="Popup" aria-modal="true" role="dialog">
            <div class="modal-dialog d-flex">
                <div class="modal-content oe_structure">
                    <div class="s_popup_close js_close_popup o_we_no_overlay o_not_editable" aria-label="Close">×</div>
                    <section><p>Popup content</p></section>
                </div>
            </div>
        </div>
    </div>`;

    // Done in `beforeEach` because frontend JS takes too much time to load.
    beforeEach(async () => {
        await setupWebsiteBuilder("", {
            loadIframeBundles: true,
            loadAssetsFrontendJS: true,
            snippets: {
                snippet_groups: [
                    '<div name="A" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
                ],
                snippet_structure: [
                    getSnippetStructure({
                        name: "Test",
                        groupName: "a",
                        content: unformat(customPopupSnippet),
                    }),
                ],
            },
        });
    });

    test("should be able to hide a custom popup", async () => {
        await insertCategorySnippet({ group: "a", snippet: "s_popup" });
        expect(".o_add_snippet_dialog").toHaveCount(0);

        expect(":iframe .s_popup .modal").toBeVisible();
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility");

        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(".o_we_invisible_entry [data-icon='visibility']").click()
        );
        await animationFrame();
        expect(":iframe .s_popup .modal").not.toBeVisible();
        expect(".o_we_invisible_entry .oi").toHaveAttribute("data-icon", "visibility_off");
    });
});
