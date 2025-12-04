import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class AddTablePopup extends Component {
    static template = "pos_restaurant.floor_editor.add_table_popup";
    static components = { Dialog };

    static props = {
        addTable: { type: Function },
        close: { optional: false },
    };

    setup() {
        this.dialog = useService("dialog");
    }

    addTable(shape) {
        this.props.addTable(shape);
        this.props.close();
    }
}
