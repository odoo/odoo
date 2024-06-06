/** @odoo-module **/

import { Component, useState, markup } from "@odoo/owl";
import { escape, sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

export class FullscreenIndication extends Component {
    setup() {
        this.state = useState({ isVisible: false });
        this.props.bus.on('FULLSCREEN-INDICATION-SHOW', this, this.show);
        this.props.bus.on('FULLSCREEN-INDICATION-HIDE', this, this.hide);
    }

    show() {
        setTimeout(() => this.state.isVisible = true);
        this.autofade = setTimeout(() => this.state.isVisible = false, 2000);
    }

    hide() {
        if (this.state.isVisible) {
            this.state.isVisible = false;
            clearTimeout(this.autofade);
        }
    }

    get fullScreenIndicationText() {
        return markup(sprintf(escape(_t("Press %(key)s to exit full screen")), {key: "<span>esc</span>"}));
    }
}
FullscreenIndication.template = "website.FullscreenIndication";
