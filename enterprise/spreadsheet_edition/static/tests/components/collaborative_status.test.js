import { describe, expect, test } from "@odoo/hoot";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { makeMockEnv, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { CollaborativeStatus } from "@spreadsheet_edition/bundle/components/collaborative_status/collaborative_status";

describe.current.tags("headless");
defineSpreadsheetModels();

async function mountCollaborativeStatusComponent() {
    await mountWithCleanup(CollaborativeStatus);
}

test("not synchronized", async function () {
    await makeMockEnv({
        model: {
            getters: {
                isFullySynchronized: () => false,
                getConnectedClients: () => [{ userId: 1, name: "Alice" }],
            },
        },
    });
    await mountCollaborativeStatusComponent();

    expect(".o_spreadsheet_sync_status").toHaveText("Saving");
    expect(".o_spreadsheet_number_users").toHaveText("1");
    expect(".o_spreadsheet_number_users i.fa").toHaveClass("fa-user");
});

test("synchronized", async function () {
    await makeMockEnv({
        model: {
            getters: {
                isFullySynchronized: () => true,
                getConnectedClients: () => [{ userId: 1, name: "Alice" }],
            },
        },
    });
    await mountCollaborativeStatusComponent();

    expect(".o_spreadsheet_sync_status").toHaveText("Saved");
});

test("more than one user", async function () {
    await makeMockEnv({
        model: {
            getters: {
                isFullySynchronized: () => true,
                getConnectedClients: () => [
                    { userId: 1, name: "Alice" },
                    { userId: 2, name: "Bob" },
                ],
            },
        },
    });
    await mountCollaborativeStatusComponent();

    expect(".o_spreadsheet_number_users").toHaveText("2");
    expect(".o_spreadsheet_number_users i.fa").toHaveClass("fa-users");
});
