import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onMounted, onWillDestroy, useProps, t } from "@odoo/owl";

export class ProductsDesignPanel extends BaseOptionComponent {
    static template = "website_sale.ProductsDesignPanel";
    static components = {
        ...BaseOptionComponent.components,
    };
    props = useProps({
        label: t.string().optional("Design"),
        recordName: t.string().optional(),
        showLists: t.boolean().optional(true),
        showSecondaryImage: t.boolean().optional(false),
        openByDefault: t.boolean().optional(false),
    });

    setup() {
        super.setup();
        // TODO master: remove this flag, along with the `setPanel` mechanism it
        // was made for, nothing reads it anymore now that the gap is persisted
        // from the `--o-wsale-products-grid-gap` style property.
        this.needsDbPersistence = this.props.recordName?.length > 0;

        onMounted(() => {
            this.setupActionConnections();
            this.registerWithPlugin();
        });

        onWillDestroy(() => {
            this.unregisterFromPlugin();
        });
    }

    registerWithPlugin() {
        this.env.editor.shared.productsDesignPanel?.registerPanel(this);
    }

    unregisterFromPlugin() {
        this.env.editor.shared.productsDesignPanel?.unregisterPanel(this);
    }

    setupActionConnections() {
        // Set panel reference for setGap action
        const builderActions = this.env.editor.shared.builderActions;
        const action = builderActions.getAction('setGap');

        if (action && action.setPanel) {
            action.setPanel(this);
        }
    }
}
