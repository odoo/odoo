/** @odoo-module **/

import { registry } from '@web/core/registry';

/**
 * This service updates periodically the user presence in order for the
 * im_status to be up to date.
 */
export const imStatusService = {
    dependencies: ['bus_service', 'multi_tab', 'presence'],

    start(env, { bus_service, multi_tab, presence }) {
        const UPDATE_BUS_PRESENCE_DELAY = 30000;
        let updateBusPresenceInterval;

        function updateBusPresence() {
            const now = new Date().getTime();
            bus_service.send("update_presence", now - presence.getLastPresence());
        }

        function stopUpdatingBusPresence() {
            clearInterval(updateBusPresenceInterval);
            updateBusPresenceInterval = null;
        }

        function startUpdatingBusPresence() {
            if (updateBusPresenceInterval || !multi_tab.isOnMainTab()) {
                return;
            }
            updateBusPresence();
            updateBusPresenceInterval = setInterval(
                updateBusPresence,
                UPDATE_BUS_PRESENCE_DELAY,
            );
        }

        if (multi_tab.isOnMainTab()) {
            startUpdatingBusPresence();
        }
        multi_tab.bus.addEventListener('become_main_tab', startUpdatingBusPresence);
        bus_service.addEventListener('reconnect', startUpdatingBusPresence);
        multi_tab.bus.addEventListener('no_longer_main_tab', stopUpdatingBusPresence);
        bus_service.addEventListener('disconnect', stopUpdatingBusPresence);
    },
};

registry.category('services').add('im_status', imStatusService);
