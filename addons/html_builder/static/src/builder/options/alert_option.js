import { registry } from "@web/core/registry";

registry.category("sidebar-element-option").add("AlertOption", {
    template: "html_builder.AlertOption",
    selector: ".s_alert",
    sequence: 5,
});

registry.category("website-builder-actions").add("alertIcon", {
    apply: ({ editingElement, param: className, value }) => {
        const icon = editingElement.querySelector("i");
        icon.classList.add(className);
    },
    clean: ({ editingElement, param: className, value }) => {
        const icon = editingElement.querySelector("i");
        icon.classList.remove(className);
    },

    isActive: ({ editingElement, param: className }) => {
        const icon = editingElement.querySelector("i");
        return icon.classList.contains(className);
    },
});
