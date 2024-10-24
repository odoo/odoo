import { Component, useRef, useState } from "@odoo/owl";
import { usePosition } from "@web/core/position/position_hook";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { pick } from "@web/core/utils/objects";

const useDraggableWithoutFollow = makeDraggableHook({
    name: "useDraggable",
    onComputeParams: ({ ctx }) => {
        ctx.followCursor = false;
    },
    onWillStartDrag: ({ ctx }) => pick(ctx.current, "element"),
    onDragStart: ({ ctx }) => pick(ctx.current, "element"),
    onDrag: ({ ctx }) => pick(ctx.current, "element"),
    onDragEnd: ({ ctx }) => pick(ctx.current, "element"),
    onDrop: ({ ctx }) => pick(ctx.current, "element"),
});

export class BuilderOverlay extends Component {
    static template = "mysterious_egg.BuilderOverlay";
    setup() {
        this.overlay = useRef("overlay");
        this.target = this.props.target;
        this.size = useState({
            height: this.target.clientHeight,
            width: this.target.clientWidth,
        });
        usePosition("root", () => this.target, {
            position: "center",
            container: () => this.props.container,
            onPositioned: () => {
                this.size.height = this.target.clientHeight;
                this.size.width = this.target.clientWidth;
                this.size.paddingBottom = window
                    .getComputedStyle(this.target)
                    .getPropertyValue("padding-bottom");
                this.size.paddingTop = window
                    .getComputedStyle(this.target)
                    .getPropertyValue("padding-top");
            },
        });
        //WIP
        this.currentDraggable = {
            initialX: 0,
            initialY: 0,
            direction: "",
        };
        useDraggableWithoutFollow({
            ref: { el: window.document.body },
            elements: ".o_handle",
            onWillStartDrag: ({ x, y, element }) => {
                this.currentDraggable.intialX = x;
                this.currentDraggable.intialY = y;
                this.currentDraggable.direction = this.getCurrentDirection(element);
                this.currentDraggable.sizes = this.getSize()[this.currentDraggable.direction];

                // Find the index of the current padding class applied to the target
                const paddingDirection = this.currentDraggable.sizes[2];
                for (let i = 0; i < this.currentDraggable.sizes[0].length; i++) {
                    const paddingClass = this.currentDraggable.sizes[0][i];
                    const paddingValue = this.currentDraggable.sizes[1][i];
                    if (this.target.classList.contains(paddingClass)) {
                        this.currentDraggable.currentSizeIndex = i;
                    } else if (
                        window.getComputedStyle(this.target).getPropertyValue(paddingDirection) ===
                        paddingValue + "px"
                    ) {
                        this.currentDraggable.currentSizeIndex = i;
                    }
                }
            },
            onDragStart: (test) => {
                console.log("onDragStart", test);
            },
            onDrag: ({ x, y }) => {
                console.log("onDrag", x, y);
                const deltaX = x - this.currentDraggable.initialX;
                const deltaY = y - this.currentDraggable.initialY;
                const currentSizeIndex = this.currentDraggable.currentSizeIndex;
                // const nextSizeIndex = currentSizeIndex + (deltaX > 0 ? 1 : -1);
                    // const dd = ev['page' + dir.XY] - dir.xy + dir.resize[1][dir.begin];
                    // const next = dir.current + (dir.current + 1 === dir.resize[1].length ? 0 : 1);
                    // const prev = dir.current ? (dir.current - 1) : 0;
            },
            onDrop: (test) => {
                console.log("onDrop", test);
            },
            onDragEnd: (test) => {
                console.log("onDragEnd", test);
            },
        });
    }

    getSize() {
        var nClass = "pt";
        var nProp = "padding-top";
        var sClass = "pb";
        var sProp = "padding-bottom";

        if (this.target.tagName === "HR") {
            nClass = "mt";
            nProp = "margin-top";
            sClass = "mb";
            sProp = "margin-bottom";
        }

        var grid = [];
        for (var i = 0; i <= 256 / 8; i++) {
            grid.push(i * 8);
        }
        grid.splice(1, 0, 4);
        this.grid = {
            n: [grid.map((v) => nClass + v), grid, nProp],
            s: [grid.map((v) => sClass + v), grid, sProp],
        };
        return this.grid;
    }

    getCurrentDirection(handleElement) {
        const handleClasses = handleElement.classList;
        if (handleClasses.contains("n")) {
            return "n";
        } else if (handleClasses.contains("s")) {
            return "s";
        } else if (handleClasses.contains("e")) {
            return "e";
        } else if (handleClasses.contains("w")) {
            return "w";
        } else if (handleClasses.contains("nw")) {
            return "nw";
        } else if (handleClasses.contains("ne")) {
            return "ne";
        } else if (handleClasses.contains("sw")) {
            return "sw";
        } else if (handleClasses.contains("se")) {
            return "se";
        } else {
            return "";
        }
    }
}
