import { BaseOptionComponent } from "@html_builder/core/utils";
import { onMounted, onWillDestroy, useState } from "@odoo/owl";

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
        this.state = useState({ overlayVisible: false });
        this.needsDbPersistence = this.props.recordName?.length > 0;

        onMounted(() => {
            this.setupActionConnections();
            this.registerWithPlugin();

            if (this.props.openByDefault) {
                this.openDesignOverlay();
            }
        });

        onWillDestroy(() => {
            this.unregisterFromPlugin();
        });
    }

    registerWithPlugin() {
        const plugin = this.env.editor.shared.productsDesignPanel;
        if (plugin) {
            plugin.registerPanel(this);
        }
    }

    unregisterFromPlugin() {
        const plugin = this.env.editor.shared.productsDesignPanel;
        if (plugin) {
            plugin.unregisterPanel(this);
        }
    }

    setupActionConnections() {
        // Set panel reference for setGap action
        const builderActions = this.env.editor.shared.builderActions;
        const action = builderActions.getAction('setGap');

        if (action && action.setPanel) {
            action.setPanel(this);
        }
    }

    openDesignOverlay() {
        this.state.overlayVisible = true;
    }

    closeDesignOverlay() {
        this.state.overlayVisible = false;
    }

    onBackdropClick(ev) {
        if (ev.target === ev.currentTarget) {
            this.closeDesignOverlay();
        }
    }
}
