import { DocumentationLink } from "@web/core/documentation_link/documentation_link";
import { registry } from "@web/core/registry";

export const documentationLink = {
    component: DocumentationLink,
    extractProps: ({ attrs }) => {
        const { path, label, "hide-icon": hideIcon, class: classes } = attrs;
        return {
            path,
            label,
            hideIcon: hideIcon === "True",
            class: classes,
        };
    },
    additionalClasses: ["d-inline"],
};

registry.category("view_widgets").add("documentation_link", documentationLink);
