import { registry } from "@web/core/registry";

registry.category("website-builder-actions").add("setClass", {
    isActive: ({ editingElement, params }) => {
        return editingElement.classList.contains(params);
    },
    apply: ({ editingElement, params }) => {
        editingElement.classList.add(params);
    },
    clean: ({ editingElement, params }) => {
        editingElement.classList.remove(params);
    },
});
