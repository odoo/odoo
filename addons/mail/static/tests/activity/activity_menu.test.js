import { describe, test } from "@odoo/hoot";
import { click, contains, defineMailModels, start, startServer } from "../mail_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("should update activities when opening the activity menu", async () => {
    const pyEnv = await startServer();
    await start();
    await contains(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu-counter", { count: 0 });
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        res_id: partnerId,
        res_model: "res.partner",
    });
    await click(".o_menu_systray i[aria-label='Activities']");
    await contains(".o-mail-ActivityMenu-counter", { text: "1" });
});
