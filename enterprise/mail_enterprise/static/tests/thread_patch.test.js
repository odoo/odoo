import {
    contains,
    defineMailModels,
    openFormView,
    patchUiSize,
    scroll,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineMailModels();

test("message list desc order", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "partner 1" });
    for (let i = 0; i <= 60; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.partner",
            res_id: partnerId,
        });
    }
    patchUiSize({ size: SIZES.XXL });
    await start();
    await openFormView("res.partner", partnerId);

    const messageEl = await waitFor(".o-mail-Message");
    const loadMoreButton = await waitFor("button:contains(Load More)");
    const siblings = [...messageEl.parentElement.children];

    expect(siblings.indexOf(messageEl)).toBeLessThan(siblings.indexOf(loadMoreButton), {
        message: "load more link should be after messages",
    });
    await contains(".o-mail-Message", { count: 30 });
    await scroll(".o-mail-Chatter", "bottom");
    await contains(".o-mail-Message", { count: 60 });
    await scroll(".o-mail-Chatter", 0);
    // weak test, no guaranteed that we waited long enough for potential extra messages to be loaded
    await contains(".o-mail-Message", { count: 60 });
});
