import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SelectPrinterIPPopup extends Component {
    static template = "your_module.SelectPrinterIPPopup";
    static props = ["ips", "close", "confirm"];

    setup() {
        this.dialog = useService("dialog");
        this.selectedIp = this.props.ips?.[0] || null;
    }

    choose(ip) {
        this.selectedIp = ip;
        this.render();
    }

    onConfirm() {
        this.props.confirm(this.selectedIp);
    }
}
