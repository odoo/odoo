import { EventBus, markup, reactive } from "@odoo/owl";

import { CallMethodSelectionDialog } from "@voip/mobile/call_method_selection_dialog";
import { SoftphoneContainer } from "@voip/softphone/softphone_container";
import { Softphone } from "@voip/softphone/softphone_model";
import { cleanPhoneNumber } from "@voip/utils/utils";
import { VoipSystrayItem } from "@voip/web/voip_systray_item";

import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Deferred } from "@web/core/utils/concurrency";
import { escape } from "@web/core/utils/strings";

export class Voip {
    bus = new EventBus();
    error;
    isUnloading = false;
    /**
     * Either “demo” or “prod”. In demo mode, phone calls are simulated in the
     * interface but no RTC sessions are actually established.
     *
     * @type {"demo"|"prod"}
     */
    mode;
    /**
     * The address of the PBX server. Used as the hostname in SIP URIs.
     *
     * @type {string}
     */
    pbxAddress;
    /** @type {Softphone} */
    softphone;
    /**
     * The WebSocket URL of the signaling server that will be used to
     * communicate SIP messages between Odoo and the PBX server.
     *
     * @type {string}
     */
    webSocketUrl;

    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/core/store_service").Store} */
        this.store = services["mail.store"];
        this.callService = services["voip.call"];
        this.dialog = services.dialog;
        this.orm = services.orm;
        this.busService = services.bus_service;
        this.softphone = new Softphone(this.store, this);
        this.callService.missedCalls = this.store.voipConfig?.missedCalls ?? 0;
        delete this.store.voipConfig?.missedCalls;
        Object.assign(this, this.store.voipConfig);
        delete this.store.voipConfig;
        this.busService.subscribe("delete_call_activity", (payload) => {
            const activity = this.store.Activity.insert(payload);
            activity.remove();
        });
        this.busService.subscribe("refresh_call_activities", () => {
            this.fetchTodayCallActivities();
        });
        this.busService.subscribe("voip.call/delete", (payload) => {
            for (const id of payload.ids) {
                this.store.Call.get(id)?.delete();
            }
        });
        window.addEventListener("beforeunload", this._onBeforeUnload.bind(this));
        return reactive(this);
    }

    /**
     * Determines if `voip_secret` and `voip_username` settings are defined for
     * the current user.
     *
     * @returns {boolean}
     */
    get areCredentialsSet() {
        return Boolean(this.store.settings.voip_username && this.store.settings.voip_secret);
    }

    /**
     * With some providers, the authorization username (the one used to register
     * with the PBX server) differs from the username. This getter is intended
     * to provide a way to override the authorization username.
     *
     * @returns {string}
     */
    get authorizationUsername() {
        return this.store.settings.voip_username || "";
    }

    get calls() {
        return this.store.Call.records;
    }

    /** @returns {boolean} */
    get canCall() {
        return (
            this.mode === "demo" ||
            (this.hasRtcSupport && this.isServerConfigured && this.areCredentialsSet)
        );
    }

    /** @returns {boolean} */
    get hasPendingRequest() {
        return Boolean(this._activityRpc || this._contactRpc || this._recentCallsRpc);
    }

    /** @returns {boolean} */
    get hasRtcSupport() {
        return Boolean(
            window.RTCPeerConnection && window.MediaStream && browser.navigator.mediaDevices
        );
    }

    /** @returns {boolean} */
    get hasValidExternalDeviceNumber() {
        if (!this.store.settings.external_device_number) {
            return false;
        }
        return cleanPhoneNumber(this.store.settings.external_device_number) !== "";
    }

    /**
     * Determines if `pbxAddress` and `webSocketUrl` have been provided.
     *
     * @returns {boolean}
     */
    get isServerConfigured() {
        return Boolean(this.pbxAddress && this.webSocketUrl);
    }

    /** @returns {number} */
    get missedCalls() {
        return this.callService.missedCalls;
    }

    /**
     * Determines if the `should_call_from_another_device` setting is set and if
     * an `external_device_number` has been provided.
     *
     * @returns {boolean}
     */
    get willCallFromAnotherDevice() {
        return (
            this.store.settings.should_call_from_another_device && this.hasValidExternalDeviceNumber
        );
    }

    async fetchContacts(searchTerms = "", offset = 0, limit = 13) {
        if (this._contactRpc) {
            this._contactRpc.abort();
        }
        this._contactRpc = this.orm.call("res.partner", "get_contacts", [], {
            offset,
            limit,
            search_terms: searchTerms,
        });
        try {
            const contactsData = await this._contactRpc;
            contactsData.forEach((contactData) =>
                this.store.Persona.insert({ ...contactData, type: "partner" })
            );
            this._contactRpc = null;
        } catch (error) {
            if (error.event?.type === "abort") {
                error.event.preventDefault();
            } else {
                this._contactRpc = null;
            }
        }
    }

    async fetchRecentCalls(offset = 0, limit = 13) {
        if (this._recentCallsRpc) {
            this._recentCallsRpc.abort();
        }
        this._recentCallsRpc = this.orm.call("voip.call", "get_recent_phone_calls", [], {
            offset,
            limit,
            search_terms: this.softphone.searchBarInputValue.trim(),
        });
        try {
            const callsData = await this._recentCallsRpc;
            callsData.forEach((data) => this.store.Call.insert(data));
            this._recentCallsRpc = null;
        } catch (error) {
            if (error.event?.type === "abort") {
                error.event.preventDefault();
            } else {
                this._recentCallsRpc = null;
            }
        }
    }

    async fetchTodayCallActivities() {
        if (this._activityRpc) {
            return;
        }
        this._activityRpc = this.orm.call("mail.activity", "get_today_call_activities");
        try {
            const data = await this._activityRpc;
            this.store.insert(data);
        } finally {
            this._activityRpc = null;
        }
    }

    resetMissedCalls() {
        if (this.missedCalls !== 0) {
            this.orm.call("res.users", "reset_last_seen_phone_call");
        }
        this.callService.missedCalls = 0;
    }

    resolveError() {
        this.error = null;
    }

    /**
     * Triggers an error that will be displayed in the softphone, and blocks the
     * UI by default.
     *
     * @param {string} message The error message to be displayed.
     * @param {Object} [options={}]
     * @param {boolean} [options.isNonBlocking=false] If true, the error will
     * not block the UI.
     */
    triggerError(message, { isNonBlocking = false } = {}) {
        const safeText = markup(escape(message).replaceAll("\n", "<br>"));
        this.error = { text: safeText, isNonBlocking };
    }

    /** @returns {Deferred<boolean>} */
    async willCallUsingVoip() {
        if (!isMobileOS()) {
            return true;
        }
        const callMethod = this.store.settings.how_to_call_on_mobile;
        if (callMethod !== "ask") {
            return callMethod === "voip";
        }
        const useVoip = new Deferred();
        this.dialog.add(
            CallMethodSelectionDialog,
            { useVoip },
            { onClose: () => useVoip.resolve(true) }
        );
        return useVoip;
    }

    /**
     * @param {BeforeUnloadEvent} ev
     * @returns {string|undefined}
     */
    _onBeforeUnload(ev) {
        if (!this.softphone.selectedCorrespondence?.call?.isInProgress) {
            return;
        }
        ev.preventDefault();
        return (ev.returnValue = _t(
            "There is still a call in progress, are you sure you want to leave the page?"
        ));
    }
}

export const voipService = {
    dependencies: ["bus_service", "dialog", "mail.store", "orm", "voip.call"],
    async start() {
        const isEmployee = await user.hasGroup("base.group_user");
        if (!isEmployee) {
            return {
                bus: new EventBus(),
                get canCall() {
                    return false;
                },
            };
        }
        registry.category("main_components").add("voip.SoftphoneContainer", {
            Component: SoftphoneContainer,
        });
        registry.category("systray").add("voip", { Component: VoipSystrayItem });
        return new Voip(...arguments);
    },
};

registry.category("services").add("voip", voipService);
