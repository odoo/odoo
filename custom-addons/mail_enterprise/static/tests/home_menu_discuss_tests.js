/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { DISCUSS_MENU_ID } from "@mail/../tests/helpers/test_constants";
import { start } from "@mail/../tests/helpers/test_utils";
import { makeDeferred } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";
import { doAction } from "@web/../tests/webclient/helpers";

QUnit.module("home menu (discuss)");

QUnit.test("Can open chat windows on home menu with Discuss app in background", async (assert) => {
    // Test relies on Discuss app not being actively open, so that it relies only on URL.
    // URL needs matching menu_id and action not 'menu': menu_id means app is either foreground or background
    // Discuss app in background means Discuss app is closed.
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const def = makeDeferred();
    const { webClient } = await start({
        async mockRPC(route) {
            if (route === "/mail/init_messaging") {
                await def;
            }
        },
    });
    await doAction(webClient, "menu", {
        props: {
            action: {
                params: { action: "menu", menu_id: DISCUSS_MENU_ID },
                tag: "menu",
                type: "ir.actions.client",
            },
        },
    });
    def.resolve();
    // Test opening of chat window works, which needs discuss app not being open
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
});
