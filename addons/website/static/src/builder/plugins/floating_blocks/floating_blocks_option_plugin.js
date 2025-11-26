import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { BuilderAction } from "@html_builder/core/builder_action";

export class FloatingBlocksOptionPlugin extends Plugin {
    static id = "floatingBlocksOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            FloatingBlocksRoundnessAction,
            AddFloatingBlockCardAction,
        },
    };
}

export class FloatingBlocksRoundnessAction extends BuilderAction {
    static id = "floatingBlocksRoundness";
    getValue({ editingElement }) {
        for (let x = 0; x <= 5; x++) {
            if (editingElement.classList.contains(`rounded-${x}`)) {
                return x;
            }
        }
        return 0;
    }
    apply({ editingElement, value }) {
        for (let x = 0; x <= 5; x++) {
            editingElement.classList.remove(`rounded-${x}`);
        }
        editingElement.classList.add(`rounded-${value}`);
    }
}
export class AddFloatingBlockCardAction extends BuilderAction {
    static id = "addFloatingBlockCard";
    static dependencies = ["builderOptions"];
    apply({ editingElement: el }) {
        const newCardEl = renderToElement("website.s_floating_blocks.new_card");
        const wrapperEl = el.querySelector(".s_floating_blocks_wrapper");
        wrapperEl.appendChild(newCardEl);
        newCardEl.scrollIntoView({ behavior: "smooth", block: "center" });
        this.dependencies.builderOptions.setNextTarget(newCardEl);
    }
}

registry.category("website-plugins").add(FloatingBlocksOptionPlugin.id, FloatingBlocksOptionPlugin);
