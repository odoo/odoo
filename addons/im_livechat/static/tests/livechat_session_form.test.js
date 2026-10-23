import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { contains, listenStoreFetch, waitStoreFetch, start, startServer } from "@mail/../tests/mail_test_helpers";
import { mail_store } from "@mail/../tests/mock_server/mail_mock_server";
import { describe, test } from "@odoo/hoot";

import { MockServer, mountView } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("fallback stays hidden while channel loads", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        name: "Test Session",
    });

    const { promise, resolve } = Promise.withResolvers();
    listenStoreFetch("discuss.channel", {
        async onRpc(request) {
            const res = await mail_store.bind(MockServer.current)(request);
            await promise;
            return res;
        },
    });

    await start();
    const mountPromise = mountView({
        type: "form",
        resModel: "discuss.channel",
        resId: channelId,
        arch: `<form js_class="livechat_session_form"/>`,
    });

    await contains(".o_form_view");
    await contains("span", { text: "No conversation found", count: 0 });

    resolve();
    await waitStoreFetch("discuss.channel");
    await mountPromise;

    await contains(".o-mail-Discuss");
    await contains("span", { text: "No conversation found", count: 0 });

});
