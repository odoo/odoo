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

    const rowSelector = (id) => `.o_hb_bg_options_container .o_row_draggable[data-id="${id}"]`;
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

    await contains(".o_hb_snippets_top_actions [data-action='save']").click();
    expect.verifySteps(["save portal cards"]);
});

test("replace a portal card icon without saving its template", async () => {
    onRpc("portal.entry", "web_save_multi", ({ args }) => {
        expect.step("save portal card icon");
        expect(args).toEqual([[2], [{ icon: "local_bar" }]]);
        return [];
    });
    onRpc("ir.ui.view", "save", () => {
        expect.step("save view");
        return true;
    });

    await setupWebsiteBuilder(`
        <main>
            <div class="o_portal_wrap">
                <div class="o_portal_cards">
                    <div class="o_portal_index_card" data-id="2">
                        <a><div class="o_portal_icon"><i class="oi oi-lg" data-icon="receipt_long"/></div>Invoices</a>
                    </div>
                </div>
            </div>
        </main>
    `);
    await contains(":iframe .o_portal_icon").click();
    await contains(".o_hb_options_container [data-action-id='replacePortalCardIcon']").click();
    await contains(".modal-dialog [data-icon='local_bar']").click();
    expect(":iframe .o_portal_icon i").toHaveAttribute("data-icon", "local_bar");

    await contains(".o_hb_snippets_top_actions [data-icon='undo']").click();
    expect(":iframe .o_portal_icon i").toHaveAttribute("data-icon", "receipt_long");
    await contains(".o_hb_snippets_top_actions [data-icon='redo']").click();
    expect(":iframe .o_portal_icon i").toHaveAttribute("data-icon", "local_bar");

    await contains(".o_hb_snippets_top_actions [data-action='save']").click();
    expect.verifySteps(["save portal card icon"]);
});

test("save the card list and the card icons in one call", async () => {
    onRpc("portal.entry", "search_read", () => [
        { id: 1, name: "Invoices", sequence: 10, show_in_portal: true },
    ]);
    onRpc("portal.entry", "web_save_multi", ({ args }) => {
        expect.step("save portal cards");
        expect(args).toEqual([[1], [{ sequence: 10, show_in_portal: false, icon: "local_bar" }]]);
        return [];
    });
    onRpc("ir.ui.view", "save", () => true);

    await setupWebsiteBuilder(`
        <main>
            <div class="o_portal_wrap">
                <div class="o_portal_cards">
                    <div class="o_portal_index_card" data-id="1">
                        <a><div class="o_portal_icon"><i class="oi oi-lg" data-icon="receipt_long"/></div>Invoices</a>
                    </div>
                </div>
            </div>
        </main>
    `);
    await contains(":iframe main:has(.o_portal_wrap)").click();
    await contains(`.o_row_draggable[data-id="0"] input[name="show_in_portal"]`).click();
    await contains(":iframe .o_portal_icon").click();
    await contains(".o_hb_options_container [data-action-id='replacePortalCardIcon']").click();
    await contains(".modal-dialog [data-icon='local_bar']").click();

    await contains(".o_hb_snippets_top_actions [data-action='save']").click();
    expect.verifySteps(["save portal cards"]);
});

test("icon color pickers show the rendered colors by default", async () => {
    await setupWebsiteBuilder(`
        <main>
            <div class="o_portal_wrap">
                <div class="o_portal_cards">
                    <div class="o_portal_index_card" data-id="2">
                        <a>
                            <div class="o_portal_icon" data-name="Card Icon" style="color: rgb(255, 0, 0); background-color: color-mix(in srgb, currentColor 20%, white);">
                                <i class="oi oi-lg" data-icon="receipt_long"/>
                            </div>
                            Invoices
                        </a>
                    </div>
                </div>
            </div>
        </main>
    `);
    await contains(":iframe .o_portal_icon").click();
    const row = (label) => `[data-container-title='Card Icon'] [data-label='${label}'] .o_we_color_preview`;
    expect(row("Color")).toHaveStyle({ backgroundColor: "rgb(255, 0, 0)" });
    expect(row("Background Color")).toHaveStyle({ backgroundColor: "rgb(255, 204, 204)" });
});
