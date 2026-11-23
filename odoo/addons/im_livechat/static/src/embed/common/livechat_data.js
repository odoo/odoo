/* @odoo-module */

import { session } from "@web/session";

const { isAvailable, serverUrl, options } = session.livechatData || {};
export { isAvailable, serverUrl, options };
