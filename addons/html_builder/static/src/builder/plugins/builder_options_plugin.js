import { Plugin } from "@html_editor/plugin";
import { uniqueId } from "@web/core/utils/functions";
import { isRemovable } from "./remove/remove_plugin";

export class BuilderOptionsPlugin extends Plugin {
    static id = "builder-options";
    static dependencies = ["selection", "overlay"];
    static shared = ["getContainers"];
    resources = {
        step_added_handlers: () => this.updateContainers(),
        update_containers: this.updateContainers.bind(this),
    };

    setup() {
        this.builderOptions = this.getResource("builder_options").map((option) => ({
            ...option,
            id: uniqueId(),
        }));
        this.addDomListener(this.editable, "pointerup", (e) => {
            this.updateContainers(e.target);
        });

        this.lastContainers = [];
    }

    updateContainers(target) {
        if (target) {
            this.target = target;
        }
        if (!this.target || !this.target.isConnected) {
            this.lastContainers = [];
            this.dispatchTo("change_current_options_containers_listeners", this.lastContainers);
            return;
        }
        if (this.target.dataset.invisible === "1") {
            delete this.target;
            // The element is present on a page but is not visible
            this.lastContainers = [];
            this.dispatchTo("change_current_options_containers_listeners", this.lastContainers);
            return;
        }
        const elementToOptions = new Map();
        for (const option of this.builderOptions) {
            const { selector, exclude } = option;
            let elements = getClosestElements(this.target, selector);
            if (exclude) {
                elements = elements.filter((el) => !el.matches(exclude));
            }
            for (const element of elements) {
                if (elementToOptions.has(element)) {
                    elementToOptions.get(element).push(option);
                } else {
                    elementToOptions.set(element, [option]);
                }
            }
        }

        const previousElementToIdMap = new Map(this.lastContainers.map((c) => [c.element, c.id]));
        this.lastContainers = [...elementToOptions]
            .sort(([a], [b]) => (b.contains(a) ? 1 : -1))
            .map(([element, options]) => ({
                id: previousElementToIdMap.get(element) || uniqueId(),
                element,
                options,
                isRemovable: isRemovable(element),
            }));
        this.dispatchTo("change_current_options_containers_listeners", this.lastContainers);
    }

    getContainers() {
        return this.lastContainers;
    }
}

function getClosestElements(element, selector) {
    if (!element) {
        // TODO we should remove it
        return [];
    }
    const parent = element.closest(selector);
    return parent ? [parent, ...getClosestElements(parent.parentElement, selector)] : [];
}
