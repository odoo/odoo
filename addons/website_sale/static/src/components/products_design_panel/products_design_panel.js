import { BaseOptionComponent } from "@html_builder/core/utils";
import { BuilderAction } from "@html_builder/core/builder_action";
import { useState, onMounted, onWillDestroy } from "@odoo/owl";

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

// Register actions with the main component
ProductsDesignPanel.actions = {
    classActionWithSave: ClassActionWithSuggestedAction,
    setGap: SetGapAction,
};
