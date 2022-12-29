/** @odoo-module **/

import { DialogManagerContainer } from "@mail/legacy/components/dialog_manager_container/dialog_manager_container";
import { PopoverManagerContainer } from "@mail/legacy/components/popover_manager_container/popover_manager_container";
import { messagingService } from "@mail/legacy/services/messaging_service";
import { makeMessagingToLegacyEnv } from "@mail/legacy/utils/make_messaging_to_legacy_env";

import { registry } from "@web/core/registry";

const messagingValuesService = {
    start() {
        return {};
    },
};

const serviceRegistry = registry.category("services");
serviceRegistry.add("messaging", messagingService);
serviceRegistry.add("messagingValues", messagingValuesService);
serviceRegistry.add("messaging_service_to_legacy_env", makeMessagingToLegacyEnv(owl.Component.env));

registry
    .category("main_components")
    .add("DialogManagerContainer", { Component: DialogManagerContainer });
registry
    .category("main_components")
    .add("PopoverManagerContainer", { Component: PopoverManagerContainer });
