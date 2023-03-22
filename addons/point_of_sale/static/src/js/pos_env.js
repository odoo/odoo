/* @odoo-module */

// This module is basically web.env but with added fields
// that are specific to point_of_sale and extensions.

import env from "web.env";
import concurrency from "web.concurrency";
import { JobQueue, ProxyDevice } from "@point_of_sale/js/devices";

// Create new env object base on web.env.
// Mutating this new object won't affect the original object.
export const pos_env = Object.create(env);

pos_env.proxy_queue = new JobQueue(); // used to prevent parallels communications to the proxy
pos_env.proxy = new ProxyDevice({ env: pos_env }); // used to communicate to the hardware devices via a local proxy
pos_env.posMutex = new concurrency.Mutex();
