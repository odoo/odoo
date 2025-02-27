import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class FullscreenBanner extends Component {
    static template = "discuss.fullscreenBanner";
    static props = ["enterFullscreen"];
    static LOCAL_STORAGE_KEY = "ptt_ad_banner_discarded";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.state = useState({
            wasDiscarded: false,
        });
    }

    onClickClose() {
        this.state.wasDiscarded = true;
    }

    openFullscreen() {
        this.props.enterFullscreen();
        this.state.wasDiscarded = true;
    }

    get fullscreeenText() {
        return _t("Enter full screen for a better view.");
    }

    get isVisible() {
        return !this.state.wasDiscarded && this.env.inChatWindow;
    }
}
