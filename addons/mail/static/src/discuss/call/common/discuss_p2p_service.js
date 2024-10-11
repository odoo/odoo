import { registry } from "@web/core/registry";
import { PeerToPeer } from "@mail/discuss/call/common/peer_to_peer";

export const discussP2P = {
    dependencies: ["bus_service"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        const p2p = new PeerToPeer({
            logLevel: env.debug ? "info" : undefined,
            notificationRoute: "/mail/rtc/session/notify_call_members",
        });
        services["bus_service"].subscribe(
            "discuss.channel.rtc.session/peer_notification",
            ({ sender, notifications }) => {
                for (const content of notifications) {
                    p2p.handleNotification(sender, content);
                }
            }
        );
        return p2p;
    },
};

registry.category("services").add("discuss.p2p", discussP2P);
