import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, queryOne, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addPlugin,
    defineWebsiteModels,
    insertCategorySnippet,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { Plugin } from "@html_editor/plugin";
import { insertText, redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { getSnippetStructure } from "@html_builder/../tests/helpers";
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
    // Note: for some reason, `before()` doesn't work.
    // Done in `beforeEach` because frontend JS takes too much time to load.
    beforeEach(async () => {
        await setupWebsiteBuilder("", { loadIframeBundles: true, loadAssetsFrontendJS: true });
    });
    test("dropping the popup snippet automatically displays it", async () => {
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        expect(".o_add_snippet_dialog").toHaveCount(0);
        // Check if the popup is visible.
        expect(":iframe .s_popup .modal").toHaveClass("show");
        expect(":iframe .s_popup .modal").toHaveStyle({ display: "block" });
    });
    test("hidden popup are not taken into account when moving other snippets", async () => {
        await insertCategorySnippet({ group: "intro", snippet: "s_cover" });
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye").click()
        );
        await insertCategorySnippet({ group: "intro", snippet: "s_cover" });
        await contains(":iframe .s_cover:last").click();
        expect(".o_overlay_options button.fa-angle-up").toHaveCount(1);
        expect(".o_overlay_options button.fa-angle-down").toHaveCount(0);
    });
    test("undo drop of the popup snippet remove 'overflow: hidden' (shows the scrollbar)", async () => {
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        expect(".o_add_snippet_dialog").toHaveCount(0);
        // Check if the popup is visible.
        expect(":iframe .s_popup .modal").toHaveClass("show");
        expect(":iframe .s_popup .modal").toHaveStyle({ display: "block" });
        // Check body's overflow is "hidden" (it means no scrollbar appears for it)
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });

        await contains("button.fa-undo").click();
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
        await contains("button.fa-undo").click();
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
        await contains("button.fa-repeat").click();
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
    });
});
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
                    savable_mutation_record_predicates: (record) =>
                        !(record.target.matches?.(".s_popup") && record.className === "d-none"),
                };
            }
        );
        builder = await setupWebsiteBuilder(
            `<div class="s_popup o_draggable" data-snippet="s_popup" data-name="Popup" id="sPopup">
                <div class="modal fade s_popup_middle modal_shown" style="background-color: var(--black-50)  !important; display: none;" data-show-after="5000" data-display="afterDelay" data-consents-duration="7" data-bs-focus="false" data-bs-backdrop="false" tabindex="-1" aria-label="Popup" aria-hidden="true">
                    <div class="modal-dialog d-flex">
                        <div class="modal-content oe_structure">
                            <div class="s_popup_close js_close_popup o_we_no_overlay o_not_editable" aria-label="Close" contenteditable="false">×</div>
                            <section><p>Popup content</p></section>
                        </div>
                    </div>
                </div>
            </div>`,
            {
                loadIframeBundles: true,
                loadAssetsFrontendJS: true,
            }
        );
    });

    test("editing a page with a popup snippet doesn't automatically display it", async () => {
        await advanceTime(5000);
        expect(":iframe .s_popup .modal").not.toBeVisible();
    });

    test("closing s_popup with the X button updates the invisible elements panel", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye");
        expect(":iframe .s_popup .modal").toBeVisible();
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(":iframe .s_popup div.js_close_popup").click()
        );
        expect(":iframe .s_popup .modal").not.toBeVisible();
        await animationFrame();
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye-slash");
        // Ensure that no mutations were registered in the history.
        // `addStep` return the created step, or false if there was no mutations
        expect(builder.getEditor().shared.history.addStep()).toBe(false);
    });

    test("closing s_popup with other means updates the invisible elements panel", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        // Sometimes bootstrap.js takes a bit of time to display the popup
        await waitFor(":iframe .s_popup .modal", { timeout: 1000, visible: true });
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye");
        expect(":iframe .s_popup .modal").toBeVisible();
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", async () =>
            queryOne("*:has(:iframe .s_popup) iframe")
                .contentWindow.Modal.getOrCreateInstance(queryOne(":iframe .s_popup .modal"))
                .hide()
        );
        expect(":iframe .s_popup .modal").not.toBeVisible();
        await waitFor(".o_we_invisible_entry i.fa-eye-slash");
        // Ensure that no mutations were registered in the history.
        // `addStep` return the created step, or false if there was no mutations
        expect(builder.getEditor().shared.history.addStep()).toBe(false);
    });

    test("clicking twice to show s_popup ends up consistent with the eye", async () => {
        expect(".o_we_invisible_entry i").toHaveClass("fa-eye-slash");
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            Promise.all([
                contains(".o_we_invisible_entry").click(),
                contains(".o_we_invisible_entry").click(),
            ])
        );
        // Sometimes bootstrap.js takes a bit of time to display the popup
        await waitFor(":iframe .s_popup .modal", { timeout: 1000, visible: true });
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye");
        expect(":iframe .s_popup .modal").toBeVisible();
    });

    test("editing s_popup, then closing it, then undo show it again", async () => {
        const editor = builder.getEditor();
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye");
        expect(":iframe .s_popup .modal").toBeVisible();
        setSelection({ anchorNode: queryOne(":iframe .s_popup section p"), anchorOffset: 0 });
        await insertText(editor, "Other content");
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(":iframe .s_popup div.js_close_popup").click()
        );
        await animationFrame();
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye-slash");
        expect(":iframe .s_popup .modal").not.toBeVisible();
        expect(editor.shared.history.canUndo()).toBe(true);
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () => undo(editor));
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye");
        expect(":iframe .s_popup .modal").toBeVisible();
    });

    test("undoing something on a target outside s_popup closes it", async () => {
        await insertCategorySnippet({ group: "intro", snippet: "s_cover" });
        expect(".o_add_snippet_dialog").toHaveCount(0);
        await contains(":iframe .s_cover").click();
        await contains("button:contains(Grid)").click(); // arbitrary thing to undo
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye");
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            undo(builder.getEditor())
        );
        await animationFrame();
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye-slash");
    });

    test("redo of drop of another popup hides the existing one", async () => {
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        expect(".o_we_invisible_entry:first .fa").toHaveClass("fa-eye");
        expect(".o_we_invisible_entry:last .fa").toHaveClass("fa-eye-slash");
        undo(builder.getEditor());
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            redo(builder.getEditor())
        );
        await animationFrame();
        expect(".o_we_invisible_entry:first .fa").toHaveClass("fa-eye");
        expect(".o_we_invisible_entry:last .fa").toHaveClass("fa-eye-slash");
    });

    test("clone a popup hides the clone", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        // Sometimes bootstrap.js takes a bit of time to display the popup
        await waitFor(":iframe .s_popup .modal", { timeout: 1000, visible: true });
        await contains("button.oe_snippet_clone").click();
        expect(".o_we_invisible_entry:first .fa").toHaveClass("fa-eye");
        expect(".o_we_invisible_entry:last .fa").toHaveClass("fa-eye-slash");
    });

    test("redo clone a popup hides the clone", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        // Sometimes bootstrap.js takes a bit of time to display the popup
        await waitFor(":iframe .s_popup .modal", { timeout: 1000, visible: true });
        await contains("button.oe_snippet_clone").click();
        expect(".o_we_invisible_entry:first .fa").toHaveClass("fa-eye");
        expect(".o_we_invisible_entry:last .fa").toHaveClass("fa-eye-slash");

        // :not(#sPopup) to select the new popup, that will have a random id
        await expectToTriggerEvent(":iframe .s_popup:not(#sPopup) .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        await animationFrame();
        expect(".o_we_invisible_entry:first .fa").toHaveClass("fa-eye-slash");
        expect(".o_we_invisible_entry:last .fa").toHaveClass("fa-eye");

        undo(builder.getEditor());
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye");

        redo(builder.getEditor());
        await waitFor(".o_we_invisible_entry:last .fa-eye-slash");
        expect(".o_we_invisible_entry:first .fa").toHaveClass("fa-eye");
        expect(".o_we_invisible_entry:last .fa").toHaveClass("fa-eye-slash");
    });

    test("delete the popup snippet remove 'overflow: hidden' (shows the scrollbar)", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        // Sometimes bootstrap.js takes a bit of time to display the popup
        await waitFor(":iframe .s_popup .modal", { timeout: 1000, visible: true });
        // Check body's overflow is "hidden" (it means no scrollbar appears for it)
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
        await contains(".options-container[data-container-title=Popup] button.fa-trash").click();
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
    });
    test("undo delete the popup snippet add 'overflow: hidden' (hides the scrollbar)", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        // Sometimes bootstrap.js takes a bit of time to display the popup
        await waitFor(":iframe .s_popup .modal", { timeout: 1000, visible: true });
        // Check body's overflow is "hidden" (it means no scrollbar appears for it)
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
        await contains(".options-container[data-container-title=Popup] button.fa-trash").click();
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
        undo(builder.getEditor());
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
    });
    test("redo delete the popup snippet remove 'overflow: hidden' (shows the scrollbar)", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        // Sometimes bootstrap.js takes a bit of time to display the popup
        await waitFor(":iframe .s_popup .modal", { timeout: 1000, visible: true });
        // Check body's overflow is "hidden" (it means no scrollbar appears for it)
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
        await contains(".options-container[data-container-title=Popup] button.fa-trash").click();
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
        undo(builder.getEditor());
        expect(":iframe body").toHaveStyle({ overflow: "hidden" });
        redo(builder.getEditor());
        expect(":iframe body").not.toHaveStyle({ overflow: "hidden" });
    });
    test("switch to 'Theme' tab, hide popup, switch to 'Style' tab should not have the popup as target", async () => {
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        // Sometimes bootstrap.js takes a bit of time to display the popup
        await waitFor(":iframe .s_popup .modal", { timeout: 1000, visible: true });
        expect(".options-container[data-container-title=Popup]").toHaveCount(1);
        await contains("button[data-name=theme]").click();
        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye").click()
        );
        await contains("button[data-name=customize]").click();
        expect(".options-container[data-container-title=Popup]").toHaveCount(0);
    });

    test("emptied s_popup are removed and the options are updated correctly", async () => {
        const editor = builder.getEditor();
        await expectToTriggerEvent(":iframe .s_popup .modal", "shown.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye-slash").click()
        );
        await waitFor(":iframe .s_popup .modal", { visible: true });
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye");
        expect(":iframe .s_popup .modal").toBeVisible();

        await contains(":iframe section p:contains('Popup content')").click();
        await contains("div[data-container-title='Block'] button.fa-trash").click();
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
            contains(".o_we_invisible_entry .fa-eye").click()
        );
        await animationFrame();
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye-slash");

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
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye");
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
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye");

        await expectToTriggerEvent(":iframe .s_popup .modal", "hidden.bs.modal", () =>
            contains(".o_we_invisible_entry .fa-eye").click()
        );
        await animationFrame();
        expect(":iframe .s_popup .modal").not.toBeVisible();
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye-slash");
    });
});
