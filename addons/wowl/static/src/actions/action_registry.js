/** @odoo-module **/

import { displayNotificationAction } from "./client_actions";
import { Registry } from "../core/registry";

// This registry contains client actions. A client action can be either a
// Component or a function. In the former case, the given Component will be
// instantiated and mounted in the DOM. In the latter, the function will be
// executed
export const actionRegistry = odoo.actionRegistry = new Registry();

actionRegistry.add("display_notification", displayNotificationAction);
