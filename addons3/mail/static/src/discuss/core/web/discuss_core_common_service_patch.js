/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { DiscussCoreCommon, discussCoreCommon } from "../common/discuss_core_common_service";

discussCoreCommon.dependencies.push("ui");

patch(DiscussCoreCommon.prototype, {
    setup(env, services) {
        this.ui = services.ui;
        super.setup(...arguments);
    },
    insertInitChannel(channelData) {
        const thread = super.insertInitChannel(...arguments);
        if (channelData.is_minimized && channelData.state !== "closed" && !this.ui.isSmall) {
            this.store.ChatWindow.insert({
                autofocus: 0,
                folded: channelData.state === "folded",
                thread,
            });
        }
    },
});
