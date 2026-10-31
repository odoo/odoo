import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    setup() {
        super.setup(...arguments);
        this.sideChannel = fields.One("discuss.channel", { inverse: "discussAppAsSideChannel" });
        this.onChange(
            () => [this.thread, this.isActive],
            () => (this.sideChannel = undefined)
        );
    },
    shouldDisableMemberPanelAutoOpenFromClose(nextActiveAction) {
        // The thread list is used to navigate: it closes when a thread is picked.
        if (nextActiveAction?.id === "show-threads") {
            return false;
        }
        return super.shouldDisableMemberPanelAutoOpenFromClose(...arguments);
    },
});
