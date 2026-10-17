import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { patchModel } from "@mail/model/export";

export const discussChannelPatch = patchModel(DiscussChannel, {
    setup() {
        super.setup(...arguments);
        this.isDisplayedInDiscussAppDesktop = this.computed(() =>
            Boolean(
                this.discussAppAsThread &&
                    this.store.discuss.isActive &&
                    !this.store.env.services.ui.isSmall
            )
        );
    },
    computeIsDisplayed() {
        return this.isDisplayedInDiscussAppDesktop || super.computeIsDisplayed();
    },
});
