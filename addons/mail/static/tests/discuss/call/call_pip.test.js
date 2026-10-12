import {
    click,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("Call has Picture-in-picture feature", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await waitFor(".o-discuss-Call:count(1)");
    await click(".o-discuss-CallActionList button[title='More']");
    await waitFor("[name='picture-in-picture']:count(1)");
});
