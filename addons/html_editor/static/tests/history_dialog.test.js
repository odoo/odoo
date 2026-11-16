import { HistoryDialog } from "@html_editor/components/history_dialog/history_dialog";
import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { markup } from "@odoo/owl";
import { getService, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";

test("HistoryDialog shows the no content helper when the current content is empty", async () => {
    await mountWithCleanup(MainComponentsContainer);
    onRpc("res.partner", "read", () => [
        {
            create_date: "2023-01-01 12:00:00",
            create_uid: [1, "User"],
            description: false,
        },
    ]);

    getService("dialog").add(HistoryDialog, {
        recordId: 1,
        recordModel: "res.partner",
        historyMetadata: [],
        versionedFieldName: "description",
        noContentHelper: markup`<span>Empty description</span>`,
        restoreRequested: () => {},
    });

    await waitFor(".html-history-loaded");
    expect(".history-content-view .history-view-inner").toHaveText("Empty description");
});
