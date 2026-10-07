import {
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Call has Picture-in-picture feature", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains("[title='Start Call']:count(1)").click();
    await waitFor(".o-discuss-Call:count(1)");
    await contains(".o-discuss-CallActionList button[title='More']:count(1)").click();
    await waitFor("[name='picture-in-picture']:count(1)");
});
