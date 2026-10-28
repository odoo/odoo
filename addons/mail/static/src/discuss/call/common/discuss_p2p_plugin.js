import { BusPlugin } from "@bus/services/bus_plugin";
import { PeerToPeer } from "@mail/discuss/call/common/peer_to_peer";

import { onWillDestroy, Plugin, usePlugin } from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { services } from "@web/core/services";

export class DiscussP2PPlugin extends Plugin {
    /** @private */
    bus = usePlugin(BusPlugin);
    /** @private */
    debugMode = usePlugin(DebugModePlugin);
    /** @type {PeerToPeer} */
    p2p;

    setup() {
        this.p2p = new PeerToPeer({
            logLevel: this.debugMode.isActive() ? "info" : undefined,
            notificationRoute: "/mail/rtc/session/notify_call_members",
        });
        const unsubscribe = this.bus.subscribe(
            "discuss.channel.rtc.session/peer_notification",
            ({ sender, notifications }) => {
                for (const content of notifications) {
                    this.p2p.handleNotification(sender, content);
                }
            }
        );
        onWillDestroy(() => {
            unsubscribe();
            this.p2p.disconnect();
        });
    }
}

services.add(DiscussP2PPlugin);
