import { AWAY_DELAY } from "@mail/core/common/im_status_service";
import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

import { computed } from "@odoo/owl";

import { debounce } from "@web/core/utils/timing";

/** @typedef {'offline' | 'bot' | 'online' | 'away' | undefined} ImStatus */

const { DateTime } = luxon;

/**
 * Both ResUsers and MailGuest models need to react to `presence_status` updates and
 * debounce updates to their `im_status` field to avoid flickering. This common class
 * groups the logic used by both models.
 */
export class ImStatusMixin extends Record {
    static IM_STATUS_DEBOUNCE_DELAY = 1500;

    setup() {
        super.setup();
        this.onChange(
            () => [
                this.presence_status,
                this.eq(this.store.self_user) || this.eq(this.store.self_guest),
            ],
            function onChangePresenceStatus(presence_status, isSelf) {
                if (!isSelf) {
                    return;
                }
                const presenceService = this.store.env.services.presence;
                const isOnline = presenceService.getInactivityPeriod() < AWAY_DELAY;
                if ((presence_status === "away" && isOnline) || presence_status === "offline") {
                    this.store.env.services.im_status.updateBusPresence();
                }
            }
        );
        const presenceChannel = computed(() => this.monitorPresence && this.presenceChannel);
        this.onChange(
            () => [presenceChannel(), this.store.env.services.bus_service],
            function onChangePresenceChannel(presenceChannel, busService) {
                if (presenceChannel) {
                    busService.addChannel(presenceChannel);
                    return () => busService.deleteChannel(presenceChannel);
                }
            }
        );
        this.onChange(
            () => [this.im_status],
            function onChangeImStatus(imStatus) {
                // Flickering occurs during im_status correction when switching from
                // away/offline to online. If we don't know the status, or if the status is
                // already "online", flickering cannot occur, so it's better to update the
                // field immediately.
                if (this.imStatusUI === undefined || imStatus === "online") {
                    this.forceImStatus(imStatus);
                } else {
                    this.setImStatusDebounced(imStatus);
                }
            },
            { immediate: true }
        );
        this.onChange(
            () => [this.imStatusUI === "offline"],
            function onChangeImStatusUI(isOffline) {
                this.offline_since = isOffline ? DateTime.now() : null;
            },
            { immediate: true }
        );
    }
    /**
     * Debounced write of `imStatusUI`: declared, so each record holds one
     * debounced call instead of making a new one on every read.
     *
     * @type {(status) => void}
     */
    setImStatusDebounced = this.computed(() =>
        debounce((status) => (this.imStatusUI = status), ImStatusMixin.IM_STATUS_DEBOUNCE_DELAY)
    );
    get cancelSetImStatusDebounced() {
        return this.setImStatusDebounced.cancel;
    }
    /** @type {ImStatus} */
    im_status = undefined;
    /**
     * Debounced im_status, to avoid flickering. Should be used whenever the im_status has
     * an impact on the UI.
     * @type {ImStatus}
     */
    imStatusUI = undefined;
    /** @type {string|undefined} */
    im_status_access_token;
    monitorPresence = this.computed(() => this._computeMonitorPresence());
    offline_since = fields.Datetime();
    /** @type {ImStatus} */
    presence_status;
    presenceChannel = this.computed(() => {
        const channel = `odoo-presence-${this.Model.getName()}_${this.id}`;
        if (this.im_status_access_token) {
            return channel + `-${this.im_status_access_token}`;
        }
        return channel;
    });

    _computeMonitorPresence() {
        return this.store.env.services.bus_service.isActive && this.id > 0;
    }

    forceImStatus(status) {
        this.cancelSetImStatusDebounced();
        this.imStatusUI = status;
    }
}
