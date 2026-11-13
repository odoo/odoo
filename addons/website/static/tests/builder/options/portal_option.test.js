import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("reorder and toggle portal cards before saving", async () => {
    onRpc("portal.entry", "search_read", () => [
        { id: 1, name: "First", sequence: 10, show_in_portal: true },
        { id: 2, name: "Second", sequence: 20, show_in_portal: true },
        { id: 3, name: "Third", sequence: 30, show_in_portal: true },
    ]);
    onRpc("portal.entry", "web_save_multi", ({ args }) => {
        expect.step("save portal cards");
        expect(args).toEqual([
            [2, 1, 3],
            [
                { sequence: 10, show_in_portal: true },
                { sequence: 20, show_in_portal: true },
                { sequence: 30, show_in_portal: false },
            ],
        ]);
        return [];
    });
    onRpc("ir.ui.view", "save", () => true);

    // Initial order: 1, 2, 3.
    const { getEditor } = await setupWebsiteBuilder(`
        <main>
            <div class="o_portal_wrap">
                <div class="o_portal_cards">
                    <div class="o_portal_index_card" data-id="1"><a>First</a></div>
                    <div class="o_portal_index_card" data-id="2"><a>Second</a></div>
                    <div class="o_portal_index_card" data-id="3"><a>Third</a></div>
                </div>
            </div>
        </main>
    `);
    await contains(":iframe main:has(.o_portal_wrap)").click();

    // Reorder: 2, 1, 3.
    const rowSelector = (id) => `.o_hb_bg_options_container .o_row_draggable[data-id="${id}"]`;
    await contains(`${rowSelector(0)} .o_handle_cell`).dragAndDrop(rowSelector(1));
    expect(":iframe .o_portal_index_card:nth-child(1)").toHaveAttribute("data-id", "2");
    expect(":iframe .o_portal_index_card:nth-child(2)").toHaveAttribute("data-id", "1");
    expect(":iframe .o_portal_index_card:nth-child(3)").toHaveAttribute("data-id", "3");
    expect.verifySteps([]);

    // Undo reorder -> 1, 2, 3.
    undo(getEditor());
    await animationFrame();
    expect(":iframe .o_portal_index_card:nth-child(1)").toHaveAttribute("data-id", "1");
    expect(":iframe .o_portal_index_card:nth-child(2)").toHaveAttribute("data-id", "2");
    expect(":iframe .o_portal_index_card:nth-child(3)").toHaveAttribute("data-id", "3");

    // Redo reorder -> 2, 1, 3.
    redo(getEditor());
    await animationFrame();
    expect(":iframe .o_portal_index_card:nth-child(1)").toHaveAttribute("data-id", "2");
    expect(":iframe .o_portal_index_card:nth-child(2)").toHaveAttribute("data-id", "1");
    expect(":iframe .o_portal_index_card:nth-child(3)").toHaveAttribute("data-id", "3");

    // Toggle 2 -> hidden.
    await contains(`${rowSelector(1)} input[name="show_in_portal"]`).click();
    expect(":iframe .o_portal_index_card[data-id='2']").toHaveClass("d-none");
    expect.verifySteps([]);

    // Toggle 2 again -> shown.
    await contains(`${rowSelector(1)} input[name="show_in_portal"]`).click();
    expect(":iframe .o_portal_index_card[data-id='2']").not.toHaveClass("d-none");
    expect.verifySteps([]);

    // Toggle 3 -> hidden.
    await contains(`${rowSelector(2)} input[name="show_in_portal"]`).click();
    expect(":iframe .o_portal_index_card[data-id='3']").toHaveClass("d-none");
    expect.verifySteps([]);

    // Undo toggle 3 -> shown.
    undo(getEditor());
    await animationFrame();
    expect(":iframe .o_portal_index_card[data-id='3']").not.toHaveClass("d-none");

    // Redo toggle 3 -> hidden.
    redo(getEditor());
    await animationFrame();
    expect(":iframe .o_portal_index_card[data-id='3']").toHaveClass("d-none");

    // Save.
    await contains(".o_hb_snippets_top_actions [data-action='save']").click();
    expect.verifySteps(["save portal cards"]);
});

test("should preview, undo and redo portal card gaps", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `<main><div class="o_portal_wrap"><div class="o_portal_cards">
            <div class="o_portal_index_card" data-id="1"><a href="#">First</a></div>
        </div></div></main>`,
        // Set an initial gap.
        { styleContent: ":root { font-size: 16px; --portal-card-gap: 1rem; }" }
    );
    const editor = getEditor();
    const builderActions = editor.shared.builderActions;
    const setPortalGapAction = builderActions.getAction("setPortalCardGap");
    const getGap = setPortalGapAction.getValue.bind(setPortalGapAction);
    expect(getGap()).toBe("1rem");

    // Preview a gap, then cancel it.
    const { preview, revert } = editor.shared.history.makePreviewableAsyncOperation(() =>
        setPortalGapAction.apply({ value: "3rem", isPreviewing: true })
    );
    await preview();
    expect(getGap()).toBe("3rem");
    await revert();
    expect(getGap()).toBe("1rem");

    // Change the gap.
    await builderActions.applyAction("setPortalCardGap", { value: "2rem" });
    expect(getGap()).toBe("2rem");

    // Restore the initial gap.
    undo(editor);
    await animationFrame();
    expect(getGap()).toBe("1rem");

    // Restore the changed gap.
    redo(editor);
    await animationFrame();
    expect(getGap()).toBe("2rem");
});
