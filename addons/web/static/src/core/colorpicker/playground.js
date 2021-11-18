/* @odoo-module */

import { registry } from "@web/core/registry";
import { ColorPicker } from "./colorpicker";

class PlaygroundAction extends owl.Component {}
PlaygroundAction.template = owl.tags.xml`
    <div class="o_playground">
        <div class="picker_container">
            <ColorPicker />
        </div>
    </div>
`;
PlaygroundAction.style = owl.tags.css`
    .o_playground {
        display: grid;
        height: 100%;
        width: 100%;
        justify-content: center;
        align-items: center;
    }
    .picker_container {
        width: 300px;
    }
`;
PlaygroundAction.components = { ColorPicker };
registry.category("actions").add("playground_action", PlaygroundAction);

function playgroundItem({ env }) {
    return {
        type: "item",
        description: "Playground",
        callback: () => {
            env.services.action.doAction("playground_action");
        },
    };
}
registry.category("debug").category("default").add("playgroundItem", playgroundItem);
