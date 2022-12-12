/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { Deferred } from "@web/core/utils/concurrency";
import { registry } from '@web/core/registry';
import { session } from '@web/session';
import { isIosApp } from '@web/core/browser/feature_detection';
import { WORKER_VERSION } from "@bus/workers/websocket_worker";

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
    async: true,

    async start(env, { multi_tab: multiTab }) {
        if (session.dbuuid && multiTab.getSharedValue('dbuuid') !== session.dbuuid) {
            multiTab.setSharedValue('dbuuid', session.dbuuid);
            multiTab.removeSharedValue('last_notification_id');
        }
        const bus = new EventBus();
        const workerClass = 'SharedWorker' in window && !isIosApp() ? browser.SharedWorker : browser.Worker;
        const worker = new workerClass(`/bus/websocket_worker_bundle?v=${WORKER_VERSION}`, {
            name: 'SharedWorker' in window && !isIosApp() ? 'odoo:websocket_shared_worker' : 'odoo:websocket_worker',
        });
        const connectionInitializedDeferred = new Deferred();

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
            if ('SharedWorker' in window && !isIosApp()) {
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
            } else if (type === 'initialized') {
                connectionInitializedDeferred.resolve();
                return;
            }
            bus.trigger(type, data);
        }

        /**
         * Initialize the connection to the worker by sending it usefull
         * initial informations (last notification id, debug mode,
         * ...).
         */
        function initializeWorkerConnection() {
            // User_id has different values according to its origin:
            //     - frontend: number or false,
            //     - backend: array with only one number
            //     - guest page: array containing null or number
            //     - public pages: undefined
            // Let's format it in order to ease its usage:
            //     - number if user is logged, false otherwise, keep
            //       undefined to indicate session_info is not available.
            let uid = Array.isArray(session.user_id) ? session.user_id[0] : session.user_id;
            if (!uid && uid !== undefined) {
                uid = false;
            }
            send('initialize_connection', {
                debug: odoo.debug,
                lastNotificationId: multiTab.getSharedValue('last_notification_id', 0),
                uid,
            });
        }

        if ('SharedWorker' in window && !isIosApp()) {
            worker.port.start();
            worker.port.addEventListener('message', handleMessage);
        } else {
            worker.addEventListener('message', handleMessage);
        }
        initializeWorkerConnection();
        browser.addEventListener('pagehide', ({ persisted }) => {
            if (!persisted) {
                // Page is gonna be unloaded, disconnect this client
                // from the worker.
                send('leave');
            }
        });
        await connectionInitializedDeferred;

        return {
            addEventListener: bus.addEventListener.bind(bus),
            addChannel: channel => {
                send('add_channel', channel);
                send('start');
            },
            deleteChannel: channel => send('delete_channel', channel),
            forceUpdateChannels: () => send('force_update_channels'),
            trigger: bus.trigger.bind(bus),
            removeEventListener: bus.removeEventListener.bind(bus),
            send: (eventName, data) => send('send', { event_name: eventName, data }),
            start: () => send('start'),
            stop: () => send('leave'),
        };
    },
};
registry.category('services').add('bus_service', busService);
