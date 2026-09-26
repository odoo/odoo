import {
    click,
    contains,
    defineMailModels,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-dom";
import { onRpc, pagerNext, pagerPrevious } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("base rendering follow, edit subscription and unfollow button", async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Followers-counter:text('0')");
    await click("button[title='Show Followers'] [data-icon='person']");
    await click("button[title='Follow']:text('Follow') [data-icon='person']");
    await contains(".o-mail-Followers-counter:text('1')");
    await click("button[title='Show Followers'] .oi-filled[data-icon='person']");
    await contains(".o-mail-Followers-dropdown");
    await click(
        "button[title='Edit Notification Preferences']:text('Notifications') [data-icon='notifications']"
    );
    await contains(".o-mail-Followers-dropdown", { count: 0 });
    await click("button[title='Show Followers']");
    await click("button[title='Unfollow']:text('Unfollow') .oi-filled[data-icon='person']");
    await contains(".o-mail-Followers-counter:text('0')");
    await contains("button[title='Show Followers'] [data-icon='person']");
});

test("following during a slow RPC should not reload another record opened via the pager", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([{}, {}]);
    const subscribeDeferred = Promise.withResolvers();
    onRpc("/mail/thread/subscribe", async () => {
        expect.step("subscribe");
        await subscribeDeferred.promise;
    });
    onRpc("res.partner", "web_read", ({ args }) => expect.step(`read ${args[0][0]}`));
    await start();
    await openFormView("res.partner", partnerId_1, {
        arch: `
            <form>
                <sheet><field name="display_name"/></sheet>
                <div class="oe_chatter"><chatter/></div>
            </form>`,
        resIds: [partnerId_1, partnerId_2],
    });
    await expect.waitForSteps([`read ${partnerId_1}`]);
    await click("button[title='Show Followers']");
    await click("button[title='Follow']:text('Follow')");
    await expect.waitForSteps(["subscribe"]);
    // Switch to the second record while the subscribe RPC of the first is still pending.
    await pagerNext();
    await contains(".o_pager:text(2 / 2)");
    await expect.waitForSteps([`read ${partnerId_2}`]);
    subscribeDeferred.resolve();
    await tick();
    // The follow callback targets the first record: it must not reload the second one.
    expect.verifySteps([]);
    await pagerPrevious();
    await contains(".o-mail-Followers-counter:text('1')");
    await expect.waitForSteps([`read ${partnerId_1}`]);
});
