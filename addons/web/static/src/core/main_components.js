import { Resource, t } from "@odoo/owl";

/**
 * Main resource for global main components.
 * All main components registered here are rendered by the MainComponentsContainer.
 */
export const mainComponents = new Resource({
    name: "main_components",
    validation: t.object({
        Component: t.component(),
        props: t.object().optional(),
    }),
});
