/** @odoo-module **/

const { Component, xml, useState } = owl;

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
}
FullscreenIndication.template = xml`
<div class="o_fullscreen_indication" t-att-class="{ o_visible: state.isVisible }">
    <p>Press <span>esc</span> to exit full screen</p>
</div>`;
