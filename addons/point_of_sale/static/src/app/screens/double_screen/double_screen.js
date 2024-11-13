import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class DoubleScreen extends Component {
    static template = "point_of_sale.DoubleScreen";
    static props = {
        left: Function,
        right: Function,
        leftProps: { type: Object, optional: true },
        rightProps: { type: Object, optional: true },
    };
    static defaultProps = {
        leftProps: {},
        rightProps: {},
    };

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
    }

    get mobileSide() {
        return this.pos.mobile_pane;
    }

    get leftScreen() {
        return this.props.left;
    }

    get rightScreen() {
        return this.props.right;
    }

    get leftProps() {
        return this.props.leftProps;
    }

    get rightProps() {
        return this.props.rightProps;
    }

    get mobileComponent() {
        return this.mobileSide === "left" ? this.leftScreen : this.rightScreen;
    }

    get mobileProps() {
        return this.mobileSide === "left" ? this.leftProps : this.rightProps;
    }
}

registry.category("pos_screens").add("DoubleScreen", DoubleScreen);
