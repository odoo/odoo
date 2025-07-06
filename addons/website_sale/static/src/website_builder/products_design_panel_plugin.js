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
