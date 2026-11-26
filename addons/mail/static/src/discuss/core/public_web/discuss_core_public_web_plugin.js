import { BusPlugin } from "@bus/services/bus_plugin";
import { StorePlugin } from "@mail/core/common/store_plugin";

import { Plugin, usePlugin } from "@odoo/owl";

import { services } from "@web/core/services";

export class DiscussCorePublicWebPlugin extends Plugin {
    /** Started with the store it uses (see `StorePlugin`). */
    static sequence = 110;

    #store = usePlugin(StorePlugin);
    #busService = usePlugin(BusPlugin);

    setup() {
        this.#busService.subscribe("discuss.channel/joined", async (payload) => {
            const { store_data, channel_id } = payload;
            this.#store.insert(store_data);
            await this.#store.fetchChannel(channel_id);
        });
        window.navigator.serviceWorker?.addEventListener(
            "message",
            async ({ data: { action, data } }) => {
                if (action === "OPEN_CHANNEL") {
                    const channel = await this.#store["discuss.channel"].getOrFetch(data.id);
                    channel?.open({ focus: true });
                    if (!data.joinCall || !channel || this.#store.rtc.localChannel?.eq(channel)) {
                        return;
                    }
                    if (this.#store.rtc.localChannel) {
                        await this.#store.rtc.leaveCall();
                    }
                    await this.#store.rtc.mediaPermissionsPromise;
                    this.#store.rtc.joinCall(channel, {
                        audio: this.#store.rtc.microphonePermission === "granted",
                        camera: false,
                    });
                } else if (action === "POST_RTC_LOGS") {
                    const logs = data || {};
                    logs.odooInfo = odoo.info;
                    const string = JSON.stringify(logs);
                    const blob = new Blob([string], { type: "application/json" });
                    const downloadLink = document.createElement("a");
                    const now = luxon.DateTime.now().toFormat("yyyy-LL-dd_HH-mm");
                    downloadLink.download = `RtcLogs_${now}.json`;
                    const url = URL.createObjectURL(blob);
                    downloadLink.href = url;
                    downloadLink.click();
                    URL.revokeObjectURL(url);
                }
            }
        );
    }
}

services.add(DiscussCorePublicWebPlugin);
