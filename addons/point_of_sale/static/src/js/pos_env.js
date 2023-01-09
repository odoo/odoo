/* @odoo-module */

// This module is basically web.env but with added fields
// that are specific to point_of_sale and extensions.

import env from "web.env";
import concurrency from "web.concurrency";
import { JobQueue, ProxyDevice } from "@point_of_sale/js/devices";
import BarcodeReader from "@point_of_sale/js/barcode_reader";

// Create new env object base on web.env.
// Mutating this new object won't affect the original object.
const pos_env = Object.create(env);

pos_env.proxy_queue = new JobQueue(); // used to prevent parallels communications to the proxy
pos_env.proxy = new ProxyDevice({ env: pos_env }); // used to communicate to the hardware devices via a local proxy
pos_env.barcode_reader = new BarcodeReader({ env: pos_env, proxy: pos_env.proxy });
pos_env.posbus = new owl.EventBus();
pos_env.posMutex = new concurrency.Mutex();

export default pos_env;
