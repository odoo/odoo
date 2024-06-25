import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { memoize } from "@web/core/utils/functions";
import { RemoteConnectionError, RemoteInterface, dispatchEvent } from "./remoteHelpers";

/**
 * @return {Promise<{ SfuClient: import("@mail/static/libs/discuss_sfu/discuss_sfu").SfuClient, SFU_CLIENT_STATE: import("@mail/static/libs/discuss_sfu/discuss_sfu").SFU_CLIENT_STATE }>}
 */
const loadSfuAssets = memoize(async () => await loadBundle("mail.assets_odoo_sfu"));

const TO_ALL = -1;

export class RemoteSFU extends RemoteInterface {
    async start() {
        try {
            await loadSfuAssets();
            const sfuModule = odoo.loader.modules.get("@mail/../lib/odoo_sfu/odoo_sfu");
            this.SFU_CLIENT_STATE = sfuModule.SFU_CLIENT_STATE;
            this.sfuClient = new sfuModule.SfuClient();
            this.sfuClient.addEventListener("update", this.handleSfuClientUpdates.bind(this));
            this.sfuClient.addEventListener(
                "stateChange",
                this.handleSfuClientStateChange.bind(this)
            );
            this.sfuClient.connect(this.config.sfuConfig.url, this.config.sfuConfig.json_web_token);
        } catch (e) {
            const message = _t("Failed to load the SFU server, falling back to peer-to-peer");
            throw new RemoteConnectionError(message, e);
        }
    }
    stop() {
        this.sfuClient.disconnect();
    }
    notifyAllPeers(notificationName, notificationPayload) {
        const transportPayload = {
            toPeerId: TO_ALL,
            notificationName,
            notificationPayload,
        };
        this.sfuClient.broadcast(JSON.stringify(transportPayload));
    }
    notifyPeer(peerId, notificationName, notificationPayload) {
        const transportPayload = {
            toPeerId: peerId,
            notificationName,
            notificationPayload,
        };
        this.sfuClient.broadcast(JSON.stringify(transportPayload));
    }

    /**
     * @param {CustomEvent} param0
     * @param {Object} param0.detail
     * @param {String} param0.detail.name
     * @param {any} param0.detail.payload
     */
    async handleSfuClientUpdates({ detail }) {
        const { name, payload } = detail;
        switch (name) {
            case "disconnect": {
                const fromPeerId = payload.sessionId.split(":")[1];
                dispatchEvent(this, "remote-notification", {
                    fromPeerId,
                    notificationName: "remove_peer",
                });

                break;
            }
            case "broadcast": {
                const fromPeerId = payload.senderId.split(":")[1];
                const transportPayload = JSON.parse(payload.message);
                const { toPeerId, notificationName, notificationPayload } = transportPayload;

                if (this.config.peerId !== toPeerId && toPeerId !== TO_ALL) {
                    return;
                }
                dispatchEvent(this, "remote-notification", {
                    fromPeerId,
                    notificationName,
                    notificationPayload,
                });
                break;
            }
        }
    }
    async handleSfuClientStateChange({ detail: { state, cause } }) {
        switch (state) {
            case this.SFU_CLIENT_STATE.AUTHENTICATED:
                // if we are hot-swapping connection type, we clear the p2p as late as possible
                dispatchEvent(this, "sfu-connected");
                break;
            // todo ask tso:
            // - can a state be disconnected after being authenticated?
            // - if the state is recovering, what is the state before and after recovering?
            //   - I need that information to know if I should show/hide the avatar and selection of a peer.
            case this.SFU_CLIENT_STATE.CLOSED:
                {
                    let text;
                    if (cause === "full") {
                        text = _t("Channel full");
                    } else {
                        text = _t("Connection to SFU server closed by the server");
                    }
                    this.notification.add(text, {
                        type: "warning",
                    });
                    // todo: think about what todo in this case
                    // await this.leaveCall();
                }
                return;
        }
    }
}
