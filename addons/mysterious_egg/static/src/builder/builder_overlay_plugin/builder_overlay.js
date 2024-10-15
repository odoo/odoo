import { Component, useRef, useState } from "@odoo/owl";
import { usePosition } from "@web/core/position/position_hook";

export class BuilderOverlay extends Component {
    static template = "mysterious_egg.BuilderOverlay";
    setup() {
        this.overlay = useRef("overlay");
        this.size = useState({
            height: this.props.target.clientHeight,
            width: this.props.target.clientWidth,
        });

        usePosition("root", () => this.props.target, {
            position: "center",
            container: () => this.props.container,
            onPositioned: () => {
                this.size.height = this.props.target.clientHeight; 
                this.size.width = this.props.target.clientWidth;
            },
        });
    }
}
