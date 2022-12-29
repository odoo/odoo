/** @odoo-module **/

import { DialogManagerContainer } from "@mail/components/dialog_manager_container/dialog_manager_container";
import { ActivityMenu } from "@mail/new/activity/activity_menu";
import { DiscussClientAction } from "@mail/new/discuss/discuss_client_action";
import { ChatWindowContainer } from "@mail/new/chat/chat_window_container";
import { CallMenu } from "@mail/new/rtc/call_menu";
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
serviceRegistry.add("messaging", messagingService);
serviceRegistry.add("messagingValues", messagingValuesService);
serviceRegistry.add("systray_service", systrayService);
serviceRegistry.add("messaging_service_to_legacy_env", makeMessagingToLegacyEnv(owl.Component.env));

registry.category("actions").add("mail.action_discuss", DiscussClientAction);

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
registry.category("systray").add(
    "mail.call_menu",
    {
        Component: CallMenu,
    },
    { sequence: 100 }
);
