/** @odoo-module */

import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { createBasicChart } from "@spreadsheet/../tests/utils/commands";
import { setupCollaborativeEnv } from "../utils/collaborative_helpers";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

let alice, bob, charlie, network;

QUnit.module("spreadsheet_edition > chart collaborative", {
    async beforeEach() {
        const env = await setupCollaborativeEnv(getBasicServerData());
        alice = env.alice;
        bob = env.bob;
        charlie = env.charlie;
        network = env.network;
    },
});

QUnit.test("Chart link to odoo menu collaborative", async (assert) => {
    const chartId = "1";
    const sheetId = alice.getters.getActiveSheetId();
    createBasicChart(alice, chartId);
    await network.concurrent(() => {
        alice.dispatch("DELETE_FIGURE", { id: chartId, sheetId });
        bob.dispatch("LINK_ODOO_MENU_TO_CHART", {
            chartId,
            odooMenuId: "odooTestMenu",
        });
    });
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => user.getters.getFigures(sheetId),
        []
    );
    assert.spreadsheetIsSynchronized(
        [alice, bob, charlie],
        (user) => user.getters.getChartOdooMenu(chartId),
        undefined
    );
});
