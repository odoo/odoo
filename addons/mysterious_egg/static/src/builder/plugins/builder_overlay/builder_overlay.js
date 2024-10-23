import { Component, useRef, useState } from "@odoo/owl";
import { usePosition } from "@web/core/position/position_hook";
import { useDraggable } from "@web/core/utils/draggable";

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
                this.size.paddingBottom = window
                    .getComputedStyle(this.props.target)
                    .getPropertyValue("padding-bottom");
                this.size.paddingTop = window
                    .getComputedStyle(this.props.target)
                    .getPropertyValue("padding-top");
            },
        });
        //WIP
        useDraggable({
            ref: { el: window.document.body },
            elements: ".o_handle",
            onWillStartDrag: () => {
                console.log("onWillStartDrag", arguments);
            },
            onDragStart: ({ element }) => {
                console.log("onDragStart", arguments);
            },
            onDrag: ({ x, y, element }) => {
                console.log("onDrag", arguments);
            },
            onDrop: ({ element }) => {
                console.log("onDrop", arguments);
            },
            onDragEnd: ({ element }) => {
                console.log("onDragEnd", arguments);
            },
        });
    }

    // getSize() {
    //     var nClass = "pt";
    //     var nProp = "padding-top";
    //     var sClass = "pb";
    //     var sProp = "padding-bottom";
    //     debugger;
    //     if (this.$target.is("hr")) {
    //         nClass = "mt";
    //         nProp = "margin-top";
    //         sClass = "mb";
    //         sProp = "margin-bottom";
    //     }

    //     var grid = [];
    //     for (var i = 0; i <= 256 / 8; i++) {
    //         grid.push(i * 8);
    //     }
    //     grid.splice(1, 0, 4);
    //     this.grid = {
    //         n: [grid.map((v) => nClass + v), grid, nProp],
    //         s: [grid.map((v) => sClass + v), grid, sProp],
    //     };
    //     return this.grid;
    // }
}
