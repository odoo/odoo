import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class SyncPopup extends Component {
    static components = { Dialog };
    static template = "point_of_sale.SyncPopup";
    static props = ["close", "confirm", "title"];

    async confirm(fullReload) {
        this.props.confirm(fullReload);
        this.props.close();
    }
}
