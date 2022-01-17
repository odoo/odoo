/** @odoo-module **/

const { Component, xml, useEffect, useState } = owl;

export class FullscreenIndication extends Component {
    setup() {
        this.state = useState({ isVisible: false });

        useEffect(() => {
            setTimeout(() => this.state.isVisible = true);

            this.autofade = setTimeout(() => this.state.isVisible = false, 2000);

            return () => clearTimeout(this.autofade);
        }, () => []);
    }
}
FullscreenIndication.template = xml`
<div class="o_fullscreen_indication" t-att-class="{ o_visible: state.isVisible }">
    <p>Press <span>esc</span> to exit full screen</p>
</div>`;
