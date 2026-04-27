import { click, contains, scroll, start, startServer } from "@mail/../tests/mail_test_helpers";
import { expect, describe, test } from "@odoo/hoot";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";
import { onRpc, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test("Scrolling to bottom loads more recent calls", async () => {
    const pyEnv = await startServer();
    let rpcCount = 0;
    onRpc("voip.call", "get_recent_phone_calls", () => {
        ++rpcCount;
    });
    await start();
    for (let i = 0; i < 10; ++i) {
        pyEnv["voip.call"].create({
            phone_number: "(501) 884-5252",
            state: "terminated",
            user_id: serverState.userId,
        });
    }
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Recent" });
    await contains(".list-group-item-action", { count: 10 });
    expect(rpcCount).toBe(1);
    for (let i = 0; i < 10; ++i) {
        pyEnv["voip.call"].create({
            phone_number: "07765 862268",
            state: "terminated",
            user_id: serverState.userId,
        });
    }
    await contains(".list-group-item-action", { count: 10 });
    await scroll(".o-voip-RecentTab", "bottom");
    await contains(".list-group-item-action", { count: 20 });
    expect(rpcCount).toBe(2);
});
