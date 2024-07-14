/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class VoipSystrayItem extends Component {
    static props = {};
    static template = "voip.SystrayItem";

    setup() {
        this.voip = useState(useService("voip"));
        this.softphone = this.voip.softphone;
    }

    /**
     * Translated text used as the title attribute of the systray item.
     *
     * @returns {string}
     */
    get titleText() {
        if (this.softphone.isDisplayed) {
            if (this.softphone.isFolded) {
                return _t("Unfold Softphone");
            }
            return _t("Close Softphone");
        }
        return _t("Open Softphone");
    }

    /** @param {MouseEvent} ev */
    onClick(ev) {
        if (this.softphone.isDisplayed) {
            if (this.softphone.isFolded) {
                this.softphone.unfold();
                this.voip.resetMissedCalls();
            } else {
                this.softphone.hide();
            }
        } else {
            this.softphone.show();
            this.voip.resetMissedCalls();
        }
    }
}
