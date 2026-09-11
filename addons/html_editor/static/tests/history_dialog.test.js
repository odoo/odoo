import { HistoryDialog } from "@html_editor/components/history_dialog/history_dialog";
import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { getService, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";

test("HistoryDialog links are clickable and open in new tab", async () => {
    await mountWithCleanup(MainComponentsContainer);
    onRpc(({ method }) =>
        method === "read"
            ? [
                  {
                      create_date: "2023-01-01 12:00:00",
                      create_uid: [1, "User"],
                      description: '<a href="https://odoo.com">Link</a>',
                  },
              ]
            : ""
    );

    getService("dialog").add(HistoryDialog, {
        recordId: 1,
        recordModel: "res.partner",
        historyMetadata: [],
        versionedFieldName: "description",
        restoreRequested: () => {},
    });

    await waitFor(".html-history-loaded");
    expect(".history-content-view a").toHaveAttribute("href", "https://odoo.com");
    expect(".history-content-view a").toHaveAttribute("target", "_blank");
    expect(".history-content-view .pe-none").toHaveCount(0);
});
