import {
    click,
    contains,
    defineMailModels,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("base rendering follow, edit subscription and unfollow button", async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Followers-counter", { text: "0" });
    await contains("[title='Show Followers'] .fa-user-o");
    await click("[title='Show Followers']");
    await click(".o-dropdown-item", { text: "Follow" });
    await contains(".o-mail-Followers-counter", { text: "1" });
    await contains("[title='Show Followers'] .fa-user");
    await click("[title='Show Followers']");
    await contains(".o-mail-Followers-dropdown");
    await click("[title='Edit subscription']");
    await contains(".o-mail-Followers-dropdown", { count: 0 });
    await click("[title='Show Followers']");
    await click(".o-dropdown-item", { text: "Unfollow" });
    await contains(".o-mail-Followers-counter", { text: "0" });
    await contains("[title='Show Followers'] .fa-user-o");
});
