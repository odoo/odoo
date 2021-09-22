/** @odoo-module **/

import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";

import { browser } from "@web/core/browser/browser";
import { registry } from '@web/core/registry';

const { EventBus } = owl;
const NO_POPUP_CLOSE_CODES = [WEBSOCKET_CLOSE_CODES.SESSION_EXPIRED, WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT];

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
    dependencies: ['localization', 'notification'],

    start(env) {
        const bus = new EventBus();
        const workerClass = 'SharedWorker' in window ? browser.SharedWorker : browser.Worker;
        const worker = new workerClass('/bus/websocket_worker_bundle', {
            name: 'SharedWorker' in window ? 'odoo:websocket_shared_worker' : 'odoo:websocket_worker',
        });
        let removeConnectionLostNotification;

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
            const { type, data } = messageEv.data;
            // Do not trigger the connection lost pop up if the reconnecting
            // event is caused by a session expired/keep_alive_timeout.
            if (type === 'reconnecting' && !NO_POPUP_CLOSE_CODES.includes(data.closeCode)) {
                removeConnectionLostNotification = env.services.notification.add(
                    env._t("Websocket connection lost. Trying to reconnect..."),
                    { sticky: true },
                );
            } else if (type === 'reconnect' && removeConnectionLostNotification) {
                removeConnectionLostNotification();
                removeConnectionLostNotification = null;
            }
            bus.trigger(type, data);
        }

        if ('SharedWorker' in window) {
            worker.port.start();
            worker.port.addEventListener('message', handleMessage);
        } else {
            worker.addEventListener('message', handleMessage);
        }
        browser.addEventListener('unload', () => send('leave'));


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
