/** @odoo-module **/

import { useBus } from "@web/core/utils/hooks";
import { EventBus, Component, xml, useState } from "@odoo/owl";

export class FullscreenIndication extends Component {
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
}
FullscreenIndication.props = {
    bus: EventBus,
};
FullscreenIndication.template = xml`
<div class="o_fullscreen_indication" t-att-class="{ o_visible: state.isVisible }">
    <p>Press <span>esc</span> to exit full screen</p>
</div>`;
