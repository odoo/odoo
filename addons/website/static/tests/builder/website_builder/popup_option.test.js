import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, queryOne, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    insertCategorySnippet,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { insertText, undo } from "@html_editor/../tests/_helpers/user_actions";
import { setSelection } from "@html_editor/../tests/_helpers/selection";

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
});
describe("Popup options: popup in page before edit", () => {
    let builder;
    // Done in `beforeEach` because frontend JS takes too much time to load.
    beforeEach(async () => {
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
        // Sometimes bootstrap.js takes a bit of time to display the popup
        await waitFor(":iframe .s_popup .modal", { timeout: 1000, visible: true });
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
        // Sometimes bootstrap.js takes a bit of time to display the popup
        await waitFor(":iframe .s_popup .modal", { timeout: 1000, visible: true });
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
});
