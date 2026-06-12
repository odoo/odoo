import { Component, signal } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";

export class PttAdBanner extends Component {
    static template = "discuss.pttAdBanner";
    static LOCAL_STORAGE_KEY = "ptt_ad_banner_discarded";

    setup() {
        super.setup();
        this.pttExtService = useService("discuss.ptt_extension");
        this.store = useService("mail.store");
        this.wasDiscarded = signal(browser.localStorage.getItem(PttAdBanner.LOCAL_STORAGE_KEY));
    }

    onClickClose() {
        browser.localStorage.setItem(PttAdBanner.LOCAL_STORAGE_KEY, true);
        this.wasDiscarded.set(true);
    }

    get isVisible() {
        return (
            !this.pttExtService.isEnabled &&
            this.store.settings.usePushToTalk &&
            !isMobileOS() &&
            !this.wasDiscarded()
        );
    }
}
