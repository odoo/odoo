import { Component } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

export class ClickbotOverlay extends Component {
    static template = "web.ClickbotOverlay";
    static props = { state: Object, onClose: Function };

    onStop() {
        this.props.state.done = true;
        browser.localStorage.removeItem("running.clickbot");
    }
}
