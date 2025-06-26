import { Component, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";

export class PttAdBanner extends Component {
    static template = "discuss.pttAdBanner";
    static props = {};
    static LOCAL_STORAGE_KEY = "ptt_ad_banner_discarded";

    setup() {
        super.setup();
        this.pttExtService = useState(useService("discuss.ptt_extension"));
        this.store = useState(useService("mail.store"));
        this.state = useState({
            wasDiscarded: browser.localStorage.getItem(PttAdBanner.LOCAL_STORAGE_KEY),
        });
    }

    onClickClose() {
        browser.localStorage.setItem(PttAdBanner.LOCAL_STORAGE_KEY, true);
        this.state.wasDiscarded = true;
    }

    get isVisible() {
        return (
            !this.pttExtService.isEnabled &&
            this.store.settings.use_push_to_talk &&
            !isMobileOS() &&
            !this.state.wasDiscarded
        );
    }
}
