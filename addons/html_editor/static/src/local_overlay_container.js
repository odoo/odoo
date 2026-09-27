import { useProps, signal, t } from "@odoo/owl";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { useRegistry } from "@web/core/registry_hook";

/**
 * TODO ABD: refactor to propagate a reactive object instead of using a registry with an identifier
 */
export class LocalOverlayContainer extends MainComponentsContainer {
    static template = "html_editor.LocalOverlayContainer";
    props = useProps({
        identifier: t.string().optional("overlay_components"),
    });

    // Ref on the overlay element, either owned by the parent (`localOverlay`
    // prop) or local.
    localOverlay = useProps.static(
        "localOverlay",
        t.signal(t.ref()).optional(() => signal.ref())
    );

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
    }
}
