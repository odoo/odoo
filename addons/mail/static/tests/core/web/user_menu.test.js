import {
    click,
    defineMailModels,
    hover,
    insertText,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("User menu shows im_status icon", async () => {
    await start();
    await waitFor(".o_user_menu .o-mail-ImStatus");
});

test("set status message writes field on user", async () => {
    const pyEnv = await startServer();
    await start();
    await click(".o_user_menu");
    await hover(".dropdown-menu a:has(.o-mail-ImStatus)");
    await insertText(
        ".o-mail-ImStatusDropdown input[placeholder='e.g. Off on Wednesdays']",
        "I am busy"
    );
    await animationFrame();
    expect(
        pyEnv["res.users"].read([serverState.userId], ["status_message"])[0].status_message
    ).toBe("I am busy");
});
