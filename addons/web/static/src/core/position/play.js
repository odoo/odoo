import { Component, useRef, useState, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { usePosition } from "./position_hook";
import { useDraggable } from "../utils/draggable";
import { pick } from "../utils/objects";

const DIRECTIONS = ["top", "bottom", "left", "right"];
const VARIANTS = ["start", "middle", "end"];
const POSITIONS = DIRECTIONS.flatMap((direction) =>
    VARIANTS.map((variant) => `${direction}-${variant}`)
);

class PlayAction extends Component {
    static components = {};
    static props = ["*"];
    static template = xml`
        <div class="controls d-inline-flex">
            <select t-on-change="setPosition">
                <option t-foreach="POSITIONS" t-as="position" t-key="position_index" t-esc="position"/>
            </select>
            <button t-on-click="unlock">Unlock</button>
        </div>
        <div class="alert alert-info">
            Current position: <b t-esc="state.currentPos"/>
        </div>
        <div id="scroll-container" style="overflow: auto; height: 450px; background-color: mintcream">
            <div id="container" t-ref="container" style="background-color: bisque; display: flex; align-items: center; justify-content: center; width: 450px; height: 450px; margin: 25px">
                <div id="target" t-ref="target" style="background-color: royalblue; width: 50px; height: 50px"/>
                <div id="popper" t-ref="popper" style="background-color: maroon; height: 100px; width: 400px">
                    <div id="popper-content" style="background-color: seagreen; height: 50px; width: 50px"/>
                </div>
            </div>
        </div>
    `;
    setup() {
        this.state = useState({ currentPos: null });
        const target = useRef("target");
        const container = useRef("container");
        useDraggable({
            ref: useRef("container"),
            elements: "#target",
            onDrag: (...args) => {
                posCtrl.unlock();
            },
            onDragEnd: ({ element }) => {
                const currentPos = pick(element.style, "top", "left", "position");
                new Promise((resolve) => setTimeout(resolve)).then(() => {
                    Object.assign(element.style, currentPos);
                });
            },
        });
        let position = POSITIONS[0];
        const posCtrl = usePosition("popper", () => target?.el, {
            container: () => container?.el,
            onPositioned: (el, { direction, variant }) => {
                this.state.currentPos = `${direction}-${variant}`;
            },
            get position() {
                return position;
            },
            set position(val) {
                position = val;
            },
        });

        this.unlock = posCtrl.unlock;
        this.POSITIONS = POSITIONS;
        this.setPosition = (e) => {
            position = e.target.value;
            posCtrl.unlock();
        };
    }
}

registry.category("actions").add("playground_action", PlayAction);
registry
    .category("debug")
    .category("default")
    .add("playgroundItem", ({ env }) => ({
        type: "item",
        description: "Playground",
        callback: () => {
            env.services.action.doAction("playground_action");
        },
    }));
