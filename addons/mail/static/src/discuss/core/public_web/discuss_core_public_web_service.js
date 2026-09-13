// @ts-check
/** @odoo-module native */
import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { luxon } from "@web/core/l10n/luxon";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";

const log = makeLogger("mail.bus");
export class DiscussCorePublicWeb {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    constructor(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.busService = services.bus_service;
        this.notificationService = services.notification;
        this.rtcService = services["discuss.rtc"];
        this.busService.subscribe("discuss.channel/joined", (payload) =>
            this.onChannelJoined(payload),
        );
        browser.navigator.serviceWorker?.addEventListener(
            "message",
            /** @param {MessageEvent<{action: string, data: Object}>} ev */
            ({ data: { action, data } }) => this.onServiceWorkerMessage(action, data),
        );
    }

    /**
     * @param {Object} payload
     * @param {Object} payload.data
     * @param {number} payload.channel_id
     * @param {boolean} [payload.invite_to_rtc_call]
     * @param {number} [payload.invited_by_user_id]
     */
    async onChannelJoined({
        data,
        channel_id,
        invite_to_rtc_call,
        invited_by_user_id: invitedByUserId,
    }) {
        log.pipeline("discuss.channel/joined", () => ({
            channel_id,
            invite_to_rtc_call,
            invitedByUserId,
        }));
        this.store.insert(data);
        await this.store.fetchChannel(channel_id);
        const thread = this.store.Thread.get({
            id: channel_id,
            model: "discuss.channel",
        });
        if (
            thread &&
            invitedByUserId &&
            invitedByUserId !== this.store.selfUser?.id &&
            !invite_to_rtc_call
        ) {
            this.notificationService.add(
                _t("You have been invited to #%s", thread.displayName),
                { type: "info" },
            );
        }
    }

    /**
     * @param {string} action
     * @param {Object} data
     */
    async onServiceWorkerMessage(action, data) {
        log.pipeline("serviceWorker message", () => ({ action, data }));
        if (action === "OPEN_CHANNEL") {
            await this.openPushedChannel(data);
        } else if (action === "OPEN_RECORD") {
            this.store.Thread.insert({ model: data.model, id: data.res_id }).open({
                focus: true,
            });
        } else if (action === "POST_RTC_LOGS") {
            this.downloadRtcLogs(data);
        }
    }

    /** @param {{id: number, joinCall: boolean}} data */
    async openPushedChannel(data) {
        const channel = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: data.id,
        });
        channel?.open({ focus: true });
        if (!data.joinCall || !channel || this.rtcService.state.channel?.eq(channel)) {
            return;
        }
        log.logic("openPushedChannel joins call", () => ({
            channel: channel.localId,
            leavingCurrent: Boolean(this.rtcService.state.channel),
        }));
        if (this.rtcService.state.channel) {
            await this.rtcService.leaveCall();
        }
        this.rtcService.joinCall(channel);
    }

    /** @param {Object} [data] */
    downloadRtcLogs(data) {
        log.logic("downloadRtcLogs");
        const logs = data || {};
        logs.odooInfo = odoo.info;
        const blob = new Blob([JSON.stringify(logs)], { type: "application/json" });
        const downloadLink = document.createElement("a");
        const now = luxon.DateTime.now().toFormat("yyyy-LL-dd_HH-mm");
        downloadLink.download = `RtcLogs_${now}.json`;
        const url = URL.createObjectURL(blob);
        downloadLink.href = url;
        downloadLink.click();
        URL.revokeObjectURL(url);
    }
}

export const discussCorePublicWeb = {
    dependencies: ["bus_service", "discuss.rtc", "mail.store", "notification"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        return reactive(new DiscussCorePublicWeb(env, services));
    },
};

registry.category("services").add("discuss.core.public.web", discussCorePublicWeb);
