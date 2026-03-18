import { AWAY_DELAY } from "@mail/core/common/im_status_service";
import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";
import { effectWithCleanup } from "@mail/utils/common/misc";

import { effect } from "@web/core/utils/reactive";
import { debounce } from "@web/core/utils/timing";

/** @typedef {'offline' | 'bot' | 'online' | 'away' | 'im_partner' | undefined} ImStatus */

const { DateTime } = luxon;

/**
 * Both ResPartner and MailGuest models need to react to `presence_status` updates and
 * debounce updates to their `im_status` field to avoid flickering. This common class
 * groups the logic used by both models.
 */
export class ImStatusMixin extends Record {
    static IM_STATUS_DEBOUNCE_DELAY = 1500;

    static new() {
        /** @type {ImStatusMixin} */
        const record = super.new(...arguments);
        const setImStatusDebounced = debounce(
            (status) => (record.imStatusUI = status),
            ImStatusMixin.IM_STATUS_DEBOUNCE_DELAY
        );
        record.setImStatusDebounced = setImStatusDebounced;
        record.cancelSetImStatusDebounced = setImStatusDebounced.cancel;
        effect(
            (record, store, presenceService, statusService) => {
                if (record.notEq(store.self)) {
                    return;
                }
                const isOnline = presenceService.getInactivityPeriod() < AWAY_DELAY;
                if (
                    (record.presence_status === "away" && isOnline) ||
                    record.presence_status === "offline"
                ) {
                    statusService.updateBusPresence();
                }
            },
            [
                record,
                record.store,
                record.store.env.services.presence,
                record.store.env.services.im_status,
            ]
        );
        effectWithCleanup({
            effect: (busService, presenceChannel) => {
                if (presenceChannel) {
                    busService.addChannel(presenceChannel);
                    return () => busService.deleteChannel(presenceChannel);
                }
            },
            dependencies: (record) => [
                record.store.env.services.bus_service,
                record.monitorPresence && record.presenceChannel,
            ],
            reactiveTargets: [record],
        });
        return record;
    }
    /** @type {(status) => void} */
    setImStatusDebounced;
    /** @type {() => void} */
    cancelSetImStatusDebounced;
    /** @type {ImStatus} */
    im_status = fields.Attr(undefined, {
        onUpdate() {
            // Flickering occurs during im_status correction when switching from
            // away/offline to online. If we don't know the status, or if the status is
            // already "online", flickering cannot occur, so it's better to update the
            // field immediately.
            if (this.imStatusUI === undefined || this.im_status === "online") {
                this.forceImStatus(this.im_status);
            } else {
                this.setImStatusDebounced(this.im_status);
            }
        },
    });
    /**
     * Debounced im_status, to avoid flickering. Should be used whenever the im_status has
     * an impact on the UI.
     * @type {ImStatus}
     */
    imStatusUI = fields.Attr(undefined, {
        onUpdate() {
            this.offline_since = this.imStatusUI === "offline" ? DateTime.now() : null;
        },
    });
    /** @type {string|undefined} */
    im_status_access_token;
    monitorPresence = fields.Attr(false, {
        compute() {
            return this._computeMonitorPresence();
        },
    });
    offline_since = fields.Datetime();
    /** @type {ImStatus} */
    presence_status;
    presenceChannel = fields.Attr(undefined, {
        compute() {
            const channel = `odoo-presence-${this.Model.getName()}_${this.id}`;
            if (this.im_status_access_token) {
                return channel + `-${this.im_status_access_token}`;
            }
            return channel;
        },
    });

    _computeMonitorPresence() {
        return this.store.env.services.bus_service.isActive && this.id > 0;
    }

    forceImStatus(status) {
        this.cancelSetImStatusDebounced();
        this.imStatusUI = status;
    }
}
