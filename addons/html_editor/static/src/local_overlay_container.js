import { Component } from "@odoo/owl";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useForwardRefToParent } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { useRegistry } from "@web/core/registry_hook";

/**
 * TODO ABD: refactor to propagate a reactive object instead of using a registry with an identifier
 */
export class LocalOverlayContainer extends MainComponentsContainer {
    static template = "html_editor.LocalOverlayContainer";
    static props = {
        localOverlay: { type: Function, optional: true },
        identifier: { type: String, optional: true },
    };
    static defaultProps = {
        identifier: "overlay_components",
    };

    setup() {
        const overlayComponents = registry.category(this.props.identifier);
        overlayComponents.addValidation({
            Component: { validate: (c) => c.prototype instanceof Component },
            props: { type: Object, optional: true },
        });
        this.Components = useRegistry(overlayComponents);
        useForwardRefToParent("localOverlay");
    }
}
