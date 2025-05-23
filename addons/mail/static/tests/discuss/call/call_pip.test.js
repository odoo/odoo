import {
    click,
    contains,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    start,
    startServer,
    triggerEvents,
} from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, test } from "@odoo/hoot";
import { hover, queryFirst } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

let channelId;
let pyEnv;
beforeEach(async () => {
    mockGetMedia();
    patchWithCleanup(window, { documentPictureInPicture: undefined });
    pyEnv = await startServer();
    channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
});

test("Picture-in-picture button is available when native pip is not supported", async () => {
    await click("[title='Start Call']");
    await contains(".o-discuss-Call");
    await click("[title='More']");
    await contains("[title='Picture in Picture']");
});

test("Picture-in-picture mode shows custom pip window", async () => {
    await click("[title='Start Call']");
    await contains(".o-discuss-Call");
    await click("[title='More']");
    await click("[title='Picture in Picture']");

    await contains(".o-discuss-CallPip");
    await contains(".o-discuss-CallPip .o-discuss-Call");
});

test("Picture-in-picture window can be closed", async () => {
    await click("[title='Start Call']");
    await click("[title='More']");
    await click("[title='Picture in Picture']");

    await contains(".o-discuss-CallPip");

    await hover(".o-discuss-CallPip");
    await click(".o-discuss-CallPip-close");

    await contains(".o-discuss-CallPip", { count: 0 });
});

test("Picture-in-picture shows participant cards correctly", async () => {
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    const memberId = pyEnv["discuss.channel.member"].create({
        channel_id: channelId,
        partner_id: partnerId,
    });
    pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: memberId,
        channel_id: channelId,
    });

    await start();
    await openDiscuss(channelId);

    await click("[title='Join Call']");
    await contains(".o-discuss-Call");

    await click("[title='More']");
    await click("[title='Picture in Picture']");

    await contains(".o-discuss-CallPip");
    await contains(".o-discuss-CallPip .o-discuss-CallParticipantCard", { count: 2 });
});

test("Picture-in-picture respects minimum size constraints", async () => {
    await click("[title='Start Call']");
    await click("[title='More']");
    await click("[title='Picture in Picture']");
    await contains(".o-discuss-CallPip");
    const resizeHandle = queryFirst(".o-discuss-CallPip-resizeHandle-se");
    await triggerEvents(resizeHandle, ["mousedown"], { clientX: 400, clientY: 220 });
    await triggerEvents(document, ["mousemove"], { clientX: 50, clientY: 50 });
    await triggerEvents(document, ["mouseup"]);
    await contains(".o-discuss-CallPip");
});
