/** @odoo-module **/

import { DialogManagerContainer } from "@mail/components/dialog_manager_container/dialog_manager_container";
import { ActivityMenu } from "@mail/new/activity/activity_menu";
import { activityService } from "@mail/new/activity/activity_service";
import { Discuss } from "@mail/new/discuss/discuss";
import { messagingService as newMessagingService } from "@mail/new/messaging_service";
import { ChatWindowContainer } from "@mail/new/chat/chat_window_container";
import { MessagingMenu } from "@mail/new/messaging_menu/messaging_menu";
import { PopoverManagerContainer } from "@mail/components/popover_manager_container/popover_manager_container";
import { messagingService } from "@mail/services/messaging_service";
import { systrayService } from "@mail/services/systray_service";
import { makeMessagingToLegacyEnv } from "@mail/utils/make_messaging_to_legacy_env";

import { registry } from "@web/core/registry";

const messagingValuesService = {
    start() {
        return {};
    },
};

const serviceRegistry = registry.category("services");
serviceRegistry.add("mail.activity", activityService);
serviceRegistry.add("mail.messaging", newMessagingService);
serviceRegistry.add("messaging", messagingService);
serviceRegistry.add("messagingValues", messagingValuesService);
serviceRegistry.add("systray_service", systrayService);
serviceRegistry.add("messaging_service_to_legacy_env", makeMessagingToLegacyEnv(owl.Component.env));

registry.category("actions").add("mail.action_discuss", Discuss);

registry
    .category("main_components")
    .add("mail.ChatWindowContainer", { Component: ChatWindowContainer });
registry
    .category("main_components")
    .add("DialogManagerContainer", { Component: DialogManagerContainer });
registry
    .category("main_components")
    .add("PopoverManagerContainer", { Component: PopoverManagerContainer });

registry.category("systray").add(
    "mail.activity_menu",
    {
        Component: ActivityMenu,
    },
    { sequence: 20 }
);
registry.category("systray").add(
    "mail.messaging_menu",
    {
        Component: MessagingMenu,
    },
    { sequence: 25 }
);
