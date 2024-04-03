/** @odoo-module **/

import { browser } from '@web/core/browser/browser';
import { registry } from '@web/core/registry';

export const UPDATE_BUS_PRESENCE_DELAY = 60000;
/**
 * This service updates periodically the user presence in order for the
 * im_status to be up to date.
 *
 * In order to receive bus notifications related to im_status, one must
 * register model/ids to monitor to this service.
 */
export const imStatusService = {
    dependencies: ['bus_service', 'multi_tab', 'presence'],

    start(env, { bus_service, multi_tab, presence }) {
        const imStatusModelToIds = {};
        let updateBusPresenceTimeout;
        const throttledUpdateBusPresence = _.throttle(
            function updateBusPresence() {
                clearTimeout(updateBusPresenceTimeout);
                if (!multi_tab.isOnMainTab()) {
                    return;
                }
                const now = new Date().getTime();
                bus_service.send("update_presence", {
                    inactivity_period: now - presence.getLastPresence(),
                    im_status_ids_by_model: { ...imStatusModelToIds },
                });
                updateBusPresenceTimeout = browser.setTimeout(throttledUpdateBusPresence, UPDATE_BUS_PRESENCE_DELAY);
            },
            UPDATE_BUS_PRESENCE_DELAY
        );

        bus_service.addEventListener('connect', () => {
            // wait for im_status model/ids to be registered before starting.
            browser.setTimeout(throttledUpdateBusPresence, 250);
        });
        multi_tab.bus.addEventListener('become_main_tab', throttledUpdateBusPresence);
        bus_service.addEventListener('reconnect', throttledUpdateBusPresence);
        multi_tab.bus.addEventListener('no_longer_main_tab', () => clearTimeout(updateBusPresenceTimeout));
        bus_service.addEventListener('disconnect', () => clearTimeout(updateBusPresenceTimeout));

        return {
            /**
             * Register model/ids whose im_status should be monitored.
             * Notification related to the im_status are then sent
             * through the bus. Overwrite registration if already
             * present.
             *
             * @param {string} model model related to the given ids.
             * @param {Number[]} ids ids whose im_status should be
             * monitored.
             */
            registerToImStatus(model, ids) {
                if (!ids.length) {
                    return this.unregisterFromImStatus(model);
                }
                imStatusModelToIds[model] = ids;
            },
            /**
             * Unregister model from im_status notifications.
             *
             * @param {string} model model to unregister.
             */
            unregisterFromImStatus(model) {
                delete imStatusModelToIds[model];
            },
        };
    },
};

registry.category('services').add('im_status', imStatusService);
