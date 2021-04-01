/** @odoo-module **/

import { Registry } from "../core/registry";

export const debugRegistry = (odoo.debugRegistry = new Registry());
