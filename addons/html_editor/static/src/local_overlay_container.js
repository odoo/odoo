import { props, t } from "@odoo/owl";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useForwardRefToParent } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { useRegistry } from "@web/core/registry_hook";

/**
 * TODO ABD: refactor to propagate a reactive object instead of using a registry with an identifier
 */
export class LocalOverlayContainer extends MainComponentsContainer {
    static template = "html_editor.LocalOverlayContainer";
    props = props({
        localOverlay: t.function().optional(),
        identifier: t.string().optional("overlay_components"),
    });

    setup() {
        const overlayComponents = registry.category(this.props.identifier);
        // todo: remove this somehow
        if (!overlayComponents.validationSchema) {
            overlayComponents.addValidation(
                t.object({
                    Component: t.component(),
                    props: t.object().optional(),
                })
            );
        }
        this.Components = useRegistry(overlayComponents);
        useForwardRefToParent("localOverlay");
    }
}
