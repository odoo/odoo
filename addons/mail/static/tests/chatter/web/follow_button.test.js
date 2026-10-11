import {
    defineMailModels,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { tick, waitFor, waitForNone } from "@odoo/hoot-dom";
import { contains, onRpc, pagerNext, pagerPrevious } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("base rendering follow, edit subscription and unfollow button", async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", threadId);
    await waitFor(".o-mail-Followers-counter:text('0'):count(1)");
    await waitFor("[title='Show Followers'] [data-icon='person']:count(1)");
    await contains("[title='Show Followers']:enabled:count(1)").click();
    await contains(".o-dropdown-item:text('Follow'):count(1)").click();
    await waitFor(".o-mail-Followers-counter:text('1'):count(1)");
    await waitFor("[title='Show Followers'] .oi-filled[data-icon='person']:count(1)");
    await contains("[title='Show Followers']:enabled:count(1)").click();
    await waitFor(".o-mail-Followers-dropdown:count(1)");
    await contains("[title='Edit Notification Preferences']:count(1)").click();
    await waitForNone(".o-mail-Followers-dropdown");
    await contains("[title='Show Followers']:enabled:count(1)").click();
    await contains(".o-dropdown-item:text('Unfollow'):count(1)").click();
    await waitFor(".o-mail-Followers-counter:text('0'):count(1)");
    await waitFor("[title='Show Followers'] [data-icon='person']:count(1)");
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
    await contains("[title='Show Followers']:enabled:count(1)").click();
    await contains(".o-dropdown-item:text('Follow'):count(1)").click();
    await expect.waitForSteps(["subscribe"]);
    // Switch to the second record while the subscribe RPC of the first is still pending.
    await pagerNext();
    await waitFor(".o_pager:text(2 / 2):count(1)");
    await expect.waitForSteps([`read ${partnerId_2}`]);
    subscribeDeferred.resolve();
    await tick();
    // The follow callback targets the first record: it must not reload the second one.
    expect.verifySteps([]);
    await pagerPrevious();
    await waitFor(".o-mail-Followers-counter:text('1'):count(1)");
    await expect.waitForSteps([`read ${partnerId_1}`]);
});
