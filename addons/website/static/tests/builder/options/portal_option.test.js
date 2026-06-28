import { expect, test } from "@odoo/hoot";
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

    await setupWebsiteBuilder(`
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

    const rowSelector = (id) => `.we-bg-options-container .o_row_draggable[data-id="${id}"]`;
    await contains(`${rowSelector(0)} .o_handle_cell`).dragAndDrop(rowSelector(1));
    expect(":iframe .o_portal_index_card:nth-child(1)").toHaveAttribute("data-id", "2");
    expect(":iframe .o_portal_index_card:nth-child(2)").toHaveAttribute("data-id", "1");
    expect(":iframe .o_portal_index_card:nth-child(3)").toHaveAttribute("data-id", "3");
    expect.verifySteps([]);

    await contains(`${rowSelector(1)} input[name="show_in_portal"]`).click();
    expect(":iframe .o_portal_index_card[data-id='2']").toHaveClass("d-none");
    expect.verifySteps([]);

    await contains(`${rowSelector(1)} input[name="show_in_portal"]`).click();
    expect(":iframe .o_portal_index_card[data-id='2']").not.toHaveClass("d-none");
    expect.verifySteps([]);

    await contains(`${rowSelector(2)} input[name="show_in_portal"]`).click();
    expect(":iframe .o_portal_index_card[data-id='3']").toHaveClass("d-none");
    expect.verifySteps([]);

    await contains(".o-snippets-top-actions [data-action='save']").click();
    expect.verifySteps(["save portal cards"]);
});
