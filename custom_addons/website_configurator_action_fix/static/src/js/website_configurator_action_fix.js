/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Configurator } from "@website/client_actions/configurator/configurator";

const actionsRegistry = registry.category("actions");

if (!actionsRegistry.contains("website_configurator")) {
    actionsRegistry.add("website_configurator", Configurator);
}
