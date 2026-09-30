import { Component, useState } from "@odoo/owl";
import { resetLocalData } from "./reset_local_data";

export class CriticalPOSError extends Component {
    static template = "point_of_sale.CriticalPOSError";
    static props = { error: Object };

    setup() {
        this.state = useState({ expanded: false });
    }
    async fullReset() {
        await resetLocalData();
    }
    async copyToClipboard() {
        const text = this.state.expanded ? this.props.error.stack : this.props.error;
        if (!text) {
            return;
        }

        try {
            await navigator.clipboard.writeText(text);
        } catch (err) {
            console.error("Could not copy text: ", err);
        }
    }
    back() {
        window.history.back();
    }
}
