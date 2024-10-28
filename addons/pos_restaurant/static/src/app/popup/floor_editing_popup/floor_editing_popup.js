import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class FloorEditingPopup extends Component {
    static template = "pos_restaurant.FloorEditingPopup";
    static components = { Dialog };
    static props = {
        title: String,
        floor: Object,
        close: Function,
        getPayload: Function,
    };

    setup() {
        this.state = useState({
            name: this.props.floor.name,
            floor_prefix: this.props.floor.floor_prefix,
        });
    }

    confirm() {
        this.props.getPayload(this.state);
        this.props.close();
    }

    isValidNumber(number) {
        // Check if string contains only numbers without floating point
        return /^\d+$/.test(number);
    }
}
