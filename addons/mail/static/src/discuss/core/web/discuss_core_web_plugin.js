import { MultiTabPlugin } from "@bus/multi_tab_plugin";
import { BusPlugin } from "@bus/services/bus_plugin";
import { StorePlugin } from "@mail/core/common/store_plugin";

import { Plugin, usePlugin } from "@odoo/owl";

import { GlobalBusPlugin } from "@web/core/global_bus_plugin";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { services } from "@web/core/services";

export class DiscussCoreWebPlugin extends Plugin {
    /** Started with the store it uses (see `StorePlugin`). */
    static sequence = 110;

    #busService = usePlugin(BusPlugin);
    #bus = usePlugin(GlobalBusPlugin).bus;
    #notificationService = usePlugin(NotificationPlugin);
    #store = usePlugin(StorePlugin);
    #ui = this.#store.ui;
    #multiTab = usePlugin(MultiTabPlugin);

    setup() {
        this.#bus.addEventListener("discuss.channel/delete", ({ detail: { channel } }) => {
            for (const tab of this.#store.messagingMenu?.visibleTabs ?? []) {
                tab.init_counter_ids = tab.init_counter_ids.filter((id) => id !== channel.id);
            }
        });
        this.#busService.subscribe("res.users/connection", async ({ partnerId, username }) => {
            // If the current user invited a new user, and the new user is
            // connecting for the first time while the current user is present
            // then open a chat for the current user with the new user.
            const notification = _t("%(user)s just connected for the first time. Wish them luck!", {
                user: username,
            });
            this.#notificationService.add(notification, { type: "info" });
            if (!(await this.#multiTab.isOnMainTab())) {
                return;
            }
            const chat = await this.#store.getChat({ partnerId });
            if (chat && !this.#ui.isSmall()) {
                chat.openChatWindow({ focus: false });
            }
        });
    }
}

services.add(DiscussCoreWebPlugin);
