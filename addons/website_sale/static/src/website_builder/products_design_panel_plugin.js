import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { ProductsDesignPanel } from "./products_design_panel";

export class ProductsDesignPanelPlugin extends Plugin {
    static id = "productsDesignPanel";
    static dependencies = ["builderActions", "builderComponents"];
    static shared = ["registerPanel", "unregisterPanel"];

    resources = {
        builder_actions: {
            classActionWithSave: ClassActionWithSuggestedAction,
            setGap: SetGapAction,
        },
        builder_components: {
            ProductsDesignPanel,
        },
        handleNewRecords: this.handleMutations.bind(this),
        save_handlers: this.onSave.bind(this),
        change_current_options_containers_listeners: () => {
            this.panels.forEach((panel) => {
                if (panel.state.overlayVisible) {
                    panel.closeDesignOverlay();
                }
            });
        },

        product_design_list_to_save: {
            selector: "#o_wsale_products_grid",
            getData(el) {
                const productOptClasses = Array.from(el.classList).filter((className) =>
                    className.startsWith("o_wsale_products_opt_")
                );
                const updateData = {
                    shop_opt_products_design_classes: productOptClasses.join(" "),
                };

                const gapToSave = el.style.getPropertyValue("--o-wsale-products-grid-gap");
                if (gapToSave !== undefined) {
                    updateData.shop_gap = gapToSave;
                }
                return updateData;
            },
        },
    };

    setup() {
        this.panels = new Set();
        this.productDesignListToSave = this.getResource("product_design_list_to_save");
        this.savableSelector = this.productDesignListToSave.map((item) => item.selector).join(",");
    }

    registerPanel(panel) {
        this.panels.add(panel);
    }

    unregisterPanel(panel) {
        this.panels.delete(panel);
    }

    /**
     * Handles the flag of the closest product savable element
     * @param {Object} records - The observed mutations
     * @param {String} currentOperation - The name of the current operation
     */
    handleMutations(records, currentOperation) {
        if (currentOperation === "undo" || currentOperation === "redo") {
            // Do nothing as `o_dirty_product_design_list` has already been handled by the history
            // plugin.
            return;
        }
        for (const record of records) {
            if (record.attributeName === "contenteditable") {
                continue;
            }
            let targetEl = record.target;
            if (!targetEl.isConnected) {
                continue;
            }
            if (targetEl.nodeType !== Node.ELEMENT_NODE) {
                targetEl = targetEl.parentElement;
            }
            if (!targetEl) {
                continue;
            }
            const isSavable = targetEl.matches(this.savableSelector);
            if (!isSavable || targetEl.classList.contains("o_dirty_product_design_list")) {
                continue;
            }
            targetEl.classList.add("o_dirty_product_design_list");
        }
    }

    async onSave() {
        const dirtyProductDesignListEls = Array.from(
            this.editable.querySelectorAll(".o_dirty_product_design_list")
        );
        for (const el of dirtyProductDesignListEls) {
            const updateData = {};
            for (const { selector, getData } of this.productDesignListToSave) {
                if (!el.matches(selector)) {
                    continue;
                }
                Object.assign(updateData, getData(el));
            }

            // Save data
            if (Object.keys(updateData).length > 0) {
                await rpc("/shop/config/website", updateData);
            }
            el.classList.remove("o_dirty_product_design_list");
        }
    }
}

/**
 * Handles suggestedClasses with clean slate approach and delegates to classAction/setClassRange
 */
class ClassActionWithSuggestedAction extends BuilderAction {
    static id = "classActionWithSave";
    static dependencies = ["builderActions"];

    setup() {
        this.classAction = this.dependencies.builderActions.getAction('classAction');
        this.setClassRangeAction = this.dependencies.builderActions.getAction('setClassRange');
    }

    getPriority(context) {
        const targetAction = Array.isArray(context.params.className) ?
            this.setClassRangeAction : this.classAction;
        return targetAction.getPriority?.(context) || 0;
    }

    isApplied(context) {
        // Transform parameters to match expected format
        const { className } = context.params;

        const targetAction = Array.isArray(className) ?
            this.setClassRangeAction : this.classAction;

        // Transform context to match what the target action expects
        const delegatedContext = {
            ...context,
            params: { mainParam: className }
        };

        return targetAction.isApplied(delegatedContext);
    }

    getValue(context) {
        const { className } = context.params;
        const targetAction = Array.isArray(className) ?
            this.setClassRangeAction : this.classAction;

        const delegatedContext = {
            ...context,
            params: { mainParam: className }
        };

        return targetAction.getValue?.(delegatedContext);
    }

    apply(context) {
        const { editingElement, params: { className, suggestedClasses } } = context;

        if (suggestedClasses) {
            this.applySuggestedClasses(editingElement, suggestedClasses);
        }

        // Delegate DOM manipulation to appropriate action
        const targetAction = Array.isArray(className) ? this.setClassRangeAction : this.classAction;

        const delegatedContext = {
            ...context,
            params: { mainParam: className }
        };

        return targetAction.apply(delegatedContext);
    }

    clean(context) {
        const { editingElement, params: { className, suggestedClasses } } = context;

        if (suggestedClasses) {
            this.cleanSuggestedClasses(editingElement, suggestedClasses);
        }

        // Delegate DOM manipulation to appropriate action
        const targetAction = Array.isArray(className) ? this.setClassRangeAction : this.classAction;

        return targetAction.clean({
            ...context,
            params: { mainParam: className }
        });
    }

    /**
     * Clean slate approach: Remove ALL o_wsale_products_opt_* classes, then add positive ones from suggestedClasses
     */
    applySuggestedClasses(editingElement, suggestedClasses) {
        if (!suggestedClasses || typeof suggestedClasses !== 'string') {
            return;
        }

        // 1. Clean slate: Remove ALL existing design classes
        const currentClasses = Array.from(editingElement.classList);
        const designClasses = currentClasses.filter(cls => cls.startsWith('o_wsale_products_opt_'));
        designClasses.forEach(cls => editingElement.classList.remove(cls));

        // 2. Apply new classes
        const newClasses = suggestedClasses.trim().split(/\s+/).filter(cls => cls && !cls.startsWith('!'));
        newClasses.forEach(cls => editingElement.classList.add(cls));
    }

    /**
     * Reverse of applySuggestedClasses for clean operations
     */
    cleanSuggestedClasses(editingElement, suggestedClasses) {
        if (!suggestedClasses || typeof suggestedClasses !== 'string') {
            return;
        }

        // Remove the positive classes that were added
        const classesToRemove = suggestedClasses.trim().split(/\s+/).filter(cls => cls && !cls.startsWith('!'));
        classesToRemove.forEach(cls => editingElement.classList.remove(cls));
    }
}

class SetGapAction extends BuilderAction {
    static id = "setGap";

    isApplied() {
        return true;
    }

    getValue({ editingElement }) {
        return editingElement.style.getPropertyValue("--o-wsale-products-grid-gap");
    }

    apply({ editingElement, value }) {
        editingElement.style.setProperty("--o-wsale-products-grid-gap", value);
        if (this.panel?.needsDbPersistence) {
            editingElement.dataset.gapToSave = value;
        }
    }

    setPanel(panel) {
        this.panel = panel;
    }
}

registry.category("website-plugins").add(ProductsDesignPanelPlugin.id, ProductsDesignPanelPlugin);
