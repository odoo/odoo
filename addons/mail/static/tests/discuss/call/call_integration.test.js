import {
    click,
    contains,
    start,
    startServer,
    openDiscuss,
    mockGetMedia,
    onlineTest,
    defineMailModels,
} from "@mail/../tests/mail_test_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";
import { PeerToPeer, UPDATE_EVENT } from "@mail/discuss/call/common/peer_to_peer";

defineMailModels();

function connectionReady(p2p) {
    return new Promise((resolve) => {
        p2p.addEventListener("update", ({ detail }) => {
            if (
                detail.name === UPDATE_EVENT.CONNECTION_CHANGE &&
                detail.payload.state === "connected"
            ) {
                resolve();
            }
        });
    });
}

async function mockPeerToPeerCallEnvironment({ channelId, remoteSessionId }) {
    const env = await start();
    const rtc = env.services["discuss.rtc"];
    const localUserP2P = env.services["discuss.p2p"];
    const remoteUserP2P = new PeerToPeer({
        notificationRoute: "/mail/rtc/session/notify_call_members",
    });
    remoteUserP2P.connect(remoteSessionId, channelId);

    onRpc("/mail/rtc/session/notify_call_members", async (req) => {
        const {
            params: { peer_notifications },
        } = await req.json();
        for (const [sender, , message] of peer_notifications) {
            /**
             * This is a simplification, if more than 2 users we should check notification.target to know which user
             * should get the notification.
             */
            if (sender === rtc.selfSession.id) {
                await remoteUserP2P.handleNotification(sender, message);
            } else {
                await localUserP2P.handleNotification(sender, message);
            }
        }
    });
    const localUserConnected = connectionReady(localUserP2P);
    const remoteUserConnected = connectionReady(remoteUserP2P);
    return { localUserConnected, remoteUserConnected };
}

onlineTest("Can join a call in p2p", async (assert) => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const remoteSessionId = pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: pyEnv["discuss.channel.member"].create({
            channel_id: channelId,
            partner_id: pyEnv["res.partner"].create({ name: "Remote" }),
        }),
        channel_id: channelId,
    });
    const { localUserConnected, remoteUserConnected } = await mockPeerToPeerCallEnvironment({
        channelId,
        remoteSessionId,
    });

    await openDiscuss(channelId);
    await click("[title='Join Call']");
    await contains(".o-discuss-Call");
    await contains(".o-discuss-CallParticipantCard[title='Remote']");
    await Promise.all([localUserConnected, remoteUserConnected]);
    await contains("span[data-connection-state='connected']");
});
