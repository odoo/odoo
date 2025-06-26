import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { after } from "@html_builder/utils/option_sequence";
import { DEVICE_VISIBILITY } from "@website/builder/option_sequence";
import { renderToElement } from "@web/core/utils/render";

class FloatingBlocksOptionPlugin extends Plugin {
    static id = "floatingBlocksOptionPlugin";
    resources = {
        builder_options: [
            withSequence(after(DEVICE_VISIBILITY), {
                template: "website.FloatingBlocksOption",
                selector: ".s_floating_blocks",
            }),
        ],
        builder_actions: {
            CardRoundnessAction,
            AddCardAction,
        },
    };
}

class CardRoundnessAction extends BuilderAction {
    static id = "cardRoundness";
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

class AddCardAction extends BuilderAction {
    static id = "addCard";
    apply({ editingElement: el }) {
        const newCardEl = renderToElement("website.s_floating_blocks.new_card");
        const wrapperEl = el.querySelector(".s_floating_blocks_wrapper");
        wrapperEl.appendChild(newCardEl);
        newCardEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

registry.category("website-plugins").add(FloatingBlocksOptionPlugin.id, FloatingBlocksOptionPlugin);
