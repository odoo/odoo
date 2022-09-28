/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from '@web/core/registry';
import { session } from '@web/session';

const { EventBus } = owl;

/**
 * Communicate with a SharedWorker in order to provide a single websocket
 * connection shared across multiple tabs.
 *
 *  @emits connect
 *  @emits disconnect
 *  @emits reconnect
 *  @emits reconnecting
 *  @emits notification
 */
export const busService = {
    dependencies: ['localization', 'multi_tab'],

    start(env, { multi_tab: multiTab }) {
        if (session.dbuuid && multiTab.getSharedValue('dbuuid') !== session.dbuuid) {
            multiTab.setSharedValue('dbuuid', session.dbuuid);
            multiTab.removeSharedValue('last_notification_id');
        }
        const bus = new EventBus();
        const workerClass = 'SharedWorker' in window ? browser.SharedWorker : browser.Worker;
        const worker = new workerClass('/bus/websocket_worker_bundle', {
            name: 'SharedWorker' in window ? 'odoo:websocket_shared_worker' : 'odoo:websocket_worker',
        });

        /**
        * Send a message to the worker.
        *
        * @param {WorkerAction} action Action to be
        * executed by the worker.
        * @param {Object|undefined} data Data required for the action to be
        * executed.
        */
        function send(action, data) {
            const message = { action, data };
            if ('SharedWorker' in window) {
                worker.port.postMessage(message);
            } else {
                worker.postMessage(message);
            }
        }

        /**
         * Handle messages received from the shared worker and fires an
         * event according to the message type.
         *
         * @param {MessageEvent} messageEv
         * @param {{type: WorkerEvent, data: any}[]}  messageEv.data
         */
        function handleMessage(messageEv) {
            const { type } = messageEv.data;
            let { data } = messageEv.data;
            if (type === 'notification') {
                multiTab.setSharedValue('last_notification_id', data[data.length - 1].id);
                data = data.map(notification => notification.message);
            }
            bus.trigger(type, data);
        }

        if ('SharedWorker' in window) {
            worker.port.start();
            worker.port.addEventListener('message', handleMessage);
        } else {
            worker.addEventListener('message', handleMessage);
        }
        send('initialize_connection', {
            debug: odoo.debug,
            lastNotificationId: multiTab.getSharedValue('last_notification_id', 0),
        });
        browser.addEventListener('pagehide', ({ persisted }) => {
            if (!persisted) {
                // Page is gonna be unloaded, disconnect this client
                // from the worker.
                send('leave');
            }
        });

        return {
            addEventListener: bus.addEventListener.bind(bus),
            addChannel: channel => send('add_channel', channel),
            deleteChannel: channel => send('delete_channel', channel),
            forceUpdateChannels: () => send('force_update_channels'),
            trigger: bus.trigger.bind(bus),
            removeEventListener: bus.removeEventListener.bind(bus),
            send: (eventName, data) => send('send', { event_name: eventName, data }),
            stop: () => send('leave'),
        };
    },
};
registry.category('services').add('bus_service', busService);
