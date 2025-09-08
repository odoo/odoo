import { BaseOptionComponent } from "@html_builder/core/utils";
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
