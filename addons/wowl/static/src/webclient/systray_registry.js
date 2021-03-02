/** @odoo-module **/

import { Registry } from "../core/registry";
import { userMenu } from "./user_menu/user_menu";

export const systrayRegistry = (odoo.systrayRegistry = new Registry());

systrayRegistry.add("wowl.user_menu", userMenu);
