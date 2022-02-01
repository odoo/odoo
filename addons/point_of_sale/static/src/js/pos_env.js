/* @odoo-module alias=point_of_sale.env */

// This module is basically web.env but with added fields
// that are specific to point_of_sale and extensions.

import env from 'web.env';
import concurrency from 'web.concurrency';
import devices from 'point_of_sale.devices';
import BarcodeReader from 'point_of_sale.BarcodeReader';

// Create new env object base on web.env.
// Mutating this new object won't affect the original object.
let pos_env = Object.create(env);

pos_env.proxy_queue = new devices.JobQueue(); // used to prevent parallels communications to the proxy
pos_env.proxy = new devices.ProxyDevice({ env: pos_env }); // used to communicate to the hardware devices via a local proxy
pos_env.barcode_reader = new BarcodeReader({ env: pos_env, proxy: pos_env.proxy });
pos_env.posbus = new owl.EventBus();
pos_env.posMutex = new concurrency.Mutex();

// create a different bus that is responsible for broadcasted pos messages.
pos_env.posBroadcastBus = new owl.EventBus();

/**
 * Broadcast a message to every open pos ui from the same config.
 * Use the `onPosBroadcast` to catch the broadcasted message.
 *
 * @param {str} messageName
 * @param {any} messageValue
 */
pos_env.broadcastPosMessage = function (messageName, messageValue) {
    return this.services.rpc({
        model: 'pos.config',
        method: 'broadcast_pos_message',
        args: [[this.pos.config.id], messageName, messageValue],
    });
}

export default pos_env;
