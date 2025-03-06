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

test("base rendering follow and unfollow button", async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Followers-counter", { text: "0" });
    await click(".o-mail-Followers-button");
    await click(".o-dropdown-item", { text: "Follow"});
    await contains(".o-mail-Followers-counter", { text: "1" });
    await click(".o-mail-Followers-button");
    await contains(".o-mail-FollowerList-unfollowBtn + .o-mail-Follower-action");
    await click(".o-dropdown-item", { text: "Unfollow"});
    await contains(".o-mail-Followers-counter", { text: "0" });
});
