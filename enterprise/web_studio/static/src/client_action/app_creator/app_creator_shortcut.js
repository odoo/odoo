/** @odoo-module **/

import { registry } from "@web/core/registry";

const actionRegistry = registry.category("actions");

actionRegistry.add("action_web_studio_app_creator",
    (env) => env.services.studio.open(env.services.studio.MODES.APP_CREATOR)
);
