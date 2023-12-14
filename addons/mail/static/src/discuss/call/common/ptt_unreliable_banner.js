/* @odoo-module */

import { PttExtCanBeDownloadedText } from "@mail/discuss/call/common/ptt_ext_can_be_downloaded_text";

import { Component, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

export class PttUnreliableBanner extends Component {
    static template = "discuss.pttUnreliableBanner";
    static components = { PttExtCanBeDownloadedText };
    static LOCAL_STORAGE_KEY = "ptt_unreliable_banner_discarded";

    setup() {
        this.pttExtService = useState(useService("discuss.ptt_extension"));
        this.userSettingsService = useState(useService("mail.user_settings"));
        this.state = useState({
            wasDiscarded: browser.localStorage.getItem(PttUnreliableBanner.LOCAL_STORAGE_KEY),
        });
    }

    onClickClose() {
        browser.localStorage.setItem(PttUnreliableBanner.LOCAL_STORAGE_KEY, true);
        this.state.wasDiscarded = true;
    }

    get isVisible() {
        return (
            !this.pttExtService.isEnabled &&
            this.userSettingsService.usePushToTalk &&
            !this.state.wasDiscarded
        );
    }
}
