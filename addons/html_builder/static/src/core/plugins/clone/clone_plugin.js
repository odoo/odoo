import { Plugin } from "@html_editor/plugin";
import { isElementInViewport } from "@html_builder/utils/utils";

export class ClonePlugin extends Plugin {
    static id = "clone";
    static dependencies = ["history", "builder-options"];
    static shared = ["cloneElement"];

    resources = {
        builder_actions: this.getActions(),
    };

    // TODO find why the images should not have the clone buttons.
    setup() {}

    getActions() {
        return {
            // TODO maybe rename to cloneItem ?
            addItem: {
                apply: ({ editingElement, param: itemSelector, value: position }) => {
                    const itemEl = editingElement.querySelector(itemSelector);
                    this.cloneElement(itemEl, { position, scrollToClone: true });
                },
            },
        };
    }

    cloneElement(el, { position = "afterend", scrollToClone = false } = {}) {
        // TODO snippet_will_be_cloned ?
        // TODO cleanUI resource for each option
        const cloneEl = el.cloneNode(true);
        el.insertAdjacentElement(position, cloneEl);
        this.dependencies["builder-options"].updateContainers(cloneEl);
        this.dispatchTo("on_clone_handlers", { cloneEl: cloneEl, originalEl: el });
        if (scrollToClone && !isElementInViewport(cloneEl)) {
            cloneEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        // TODO snippet_cloned ?
        this.dependencies.history.addStep();
    }
}
