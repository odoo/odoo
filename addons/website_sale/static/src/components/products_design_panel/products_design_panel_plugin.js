import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { ProductsDesignPanel } from "./products_design_panel";

export class ProductsDesignPanelPlugin extends Plugin {
    static id = "productsDesignPanel";
    static dependencies = ["builderActions", "builderComponents"];
    static shared = ["registerPanel", "unregisterPanel"];

    resources = {
        builder_actions: ProductsDesignPanel.actions,
        builder_components: {
            ProductsDesignPanel,
        },
        save_handlers: this.onSave.bind(this),
        change_current_options_containers_listeners: () => {
            this.panels.forEach(panel => {
                if (panel.state.overlayVisible) {
                    panel.closeDesignOverlay();
                }
            });
        },
    };

    setup() {
        this.panels = new Set();
    }

    registerPanel(panel) {
        this.panels.add(panel);
    }

    unregisterPanel(panel) {
        this.panels.delete(panel);
    }

    async onSave() {
        const persistentPanels = Array.from(this.panels).filter(panel => panel.needsDbPersistence);

        for (const panel of persistentPanels) {
            const pageEl = panel.env.getEditingElement();
            const updateData = {};

            // Save gap
            if (pageEl.dataset.gapToSave !== undefined) {
                updateData.shop_gap = pageEl.dataset.gapToSave;
            }

            // Scan DOM for all classes with o_wsale_products_opt_ prefix
            const currentClasses = Array.from(pageEl.classList);
            const productOptClasses = currentClasses.filter(className =>
                className.startsWith('o_wsale_products_opt_')
            );

            // Always save the classes field (empty string if no classes found)
            updateData[panel.props.recordName] = productOptClasses.join(' ');

            // Early return only if no classes and no gap to save
            if (productOptClasses.length === 0 && pageEl.dataset.gapToSave === undefined) {
                continue;
            }

            // Save data
            if (Object.keys(updateData).length > 0) {
                await rpc("/shop/config/website", updateData);
            }
        }
    }
}

registry.category("website-plugins").add(ProductsDesignPanelPlugin.id, ProductsDesignPanelPlugin);
