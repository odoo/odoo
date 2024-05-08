/** @odoo-module **/

import { useBus } from "@web/core/utils/hooks";
import { EventBus, Component, useState, markup } from "@odoo/owl";
import { escape, sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

export class FullscreenIndication extends Component {
    static props = {
        bus: EventBus,
    };
    static template = "website.FullscreenIndication";

    setup() {
        this.state = useState({ isVisible: false });
        useBus(this.props.bus, "FULLSCREEN-INDICATION-SHOW", this.show.bind(this));
        useBus(this.props.bus, "FULLSCREEN-INDICATION-HIDE", this.hide.bind(this));
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
