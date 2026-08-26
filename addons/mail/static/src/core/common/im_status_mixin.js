import { AWAY_DELAY } from "@mail/core/common/im_status_service";
import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

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
        super.setup(...arguments);
        const setImStatusDebounced = debounce(
            (status) => (this.imStatusUI = status),
            ImStatusMixin.IM_STATUS_DEBOUNCE_DELAY
        );
        this.setImStatusDebounced = setImStatusDebounced;
        this.cancelSetImStatusDebounced = setImStatusDebounced.cancel;
        this.onChange(
            () => {
                if (this.notEq(this.store.self_user) && this.notEq(this.store.self_guest)) {
                    return [false];
                }
                const isOnline =
                    this.store.env.services.presence.getInactivityPeriod() < AWAY_DELAY;
                return [
                    (this.presence_status === "away" && isOnline) ||
                        this.presence_status === "offline",
                ];
            },
            function updateBusPresence(isPresenceOutdated) {
                if (isPresenceOutdated) {
                    this.store.env.services.im_status.updateBusPresence();
                }
            }
        );
        this.onChange(
            () => [
                this.monitorPresence ? this.presenceChannel : undefined,
                this.store.env.services.bus_service,
            ],
            function subscribeToPresenceChannel(presenceChannel, busService) {
                if (presenceChannel) {
                    busService.addChannel(presenceChannel);
                    return () => busService.deleteChannel(presenceChannel);
                }
            }
        );
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
