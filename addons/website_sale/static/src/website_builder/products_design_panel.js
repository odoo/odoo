import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onMounted, onWillDestroy } from "@odoo/owl";

export class ProductsDesignPanel extends BaseOptionComponent {
    static template = "website_sale.ProductsDesignPanel";
    static components = {
        ...BaseOptionComponent.components,
    };
    static props = {
        label: { type: String, optional: true },
        recordName: { type: String, optional: true },
        showLists: { type: Boolean, optional: true },
        showSecondaryImage: { type: Boolean, optional: true },
        openByDefault: { type: Boolean, optional: true },
    };
    static defaultProps = {
        label: "Design",
        showLists: true,
        showSecondaryImage: false,
        openByDefault: false,
    };

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
