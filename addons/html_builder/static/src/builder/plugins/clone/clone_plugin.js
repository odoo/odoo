import { Plugin } from "@html_editor/plugin";

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
                apply: ({ editingElement, param: itemSelector }) => {
                    const itemEl = editingElement.querySelector(itemSelector);
                    this.cloneElement(itemEl);
                },
            },
        };
    }

    cloneElement(el, { position = "afterend" } = {}) {
        // TODO snippet_will_be_cloned ?
        // TODO cleanUI resource for each option
        const cloneEl = el.cloneNode(true);
        el.insertAdjacentElement(position, cloneEl);
        this.dependencies["builder-options"].updateContainers(cloneEl);
        // TODO onClone resource for each option
        // TODO snippet_cloned ?
        this.dependencies.history.addStep();
    }
}
