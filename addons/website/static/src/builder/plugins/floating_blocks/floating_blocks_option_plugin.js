import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { scrollTo } from "@html_builder/utils/scrolling";

export class FloatingBlocksOptionPlugin extends Plugin {
    static id = "floatingBlocksOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            FloatingBlocksRoundnessAction,
            AddFloatingBlockCardAction,
        },
        on_prepare_drag_handlers: this.prepareDrag.bind(this),
    };

    prepareDrag() {
        // Prevent the blocks from overlapping during the drag and drop.
        const floatingBlocksEls = this.editable.querySelectorAll(".s_floating_blocks");
        floatingBlocksEls.forEach((el) => el.classList.add("o_disable_cards_overlap"));
        const restore = () => {
            floatingBlocksEls.forEach((el) => el.classList.remove("o_disable_cards_overlap"));
        };
        return restore;
    }
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
    static dependencies = ["builderOptions", "websiteBridge"];
    apply({ editingElement: el }) {
        const newCardEl = this.dependencies.websiteBridge.renderToElement(
            "website.s_floating_blocks.new_card"
        );
        const wrapperEl = el.querySelector(".s_floating_blocks_wrapper");
        wrapperEl.appendChild(newCardEl);
        const viewportHeight = this.document.defaultView.innerHeight;
        const newCardHeight = newCardEl.getBoundingClientRect().height;
        scrollTo(newCardEl, { forcedOffset: viewportHeight / 2 - newCardHeight / 2 });
        this.dependencies.builderOptions.setNextTarget(newCardEl);
    }
}

registry.category("website-plugins").add(FloatingBlocksOptionPlugin.id, FloatingBlocksOptionPlugin);
