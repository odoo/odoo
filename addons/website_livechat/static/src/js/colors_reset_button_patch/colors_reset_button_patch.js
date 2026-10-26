import { ColorsResetButton } from "@im_livechat/js/colors_reset_button/colors_reset_button";

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(ColorsResetButton.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },

    get isFollowingWebsite() {
        return Boolean(this.props.record.data.website_theme_sync_url);
    },

    get label() {
        return this.isFollowingWebsite ? _t("Restore website styles") : super.label;
    },

    async onClick() {
        if (!this.isFollowingWebsite) {
            return super.onClick();
        }
        const colors = await this.orm.call("im_livechat.channel", "get_website_theme_colors", [
            [this.props.record.resId],
        ]);
        // Saved with the rest of the form, like the default colors reset.
        await this.props.record.update(colors);
    },
});
