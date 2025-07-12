import { BaseOptionComponent } from "@html_builder/core/utils";
import { BuilderAction } from "@html_builder/core/builder_action";
import { useState, onMounted, onWillDestroy } from "@odoo/owl";

export class ProductsDesignPanel extends BaseOptionComponent {
    static template = "website_sale.ProductsDesignPanel";
    static components = {
        ...BaseOptionComponent.components,
    };
    static props = {
        isShop: { type: Boolean, optional: true },
        label: { type: String, optional: true },
    };
    static defaultProps = {
        isShop: false,
        label: "Design",
    };

    setup() {
        super.setup();
        this.state = useState({ overlayVisible: false });

        // Initialise mappings (shop context only)
        if (this.props.isShop) {
            this.classSaveMappings = new Map();
            this.templateMappings = new Map();
        }

        onMounted(() => {
            this.setupActionConnections();
            if (this.props.isShop) {
                this.registerWithPlugin();
            }
        });

        onWillDestroy(() => {
            if (this.props.isShop) {
                this.unregisterFromPlugin();
            }
        });
    }

    registerWithPlugin() {
        const plugin = this.env.editor.shared.productsDesignPanel;
        if (plugin) {
            plugin.registerShopPanel(this);
        }
    }

    unregisterFromPlugin() {
        const plugin = this.env.editor.shared.productsDesignPanel;
        if (plugin) {
            plugin.unregisterShopPanel(this);
        }
    }

    setupActionConnections() {
        // Set panel reference for each action so they can register save mappings
        const builderActions = this.env.editor.shared.builderActions;
        const actionIds = ['classActionWithSave', 'templateConfig', 'setGap'];

        for (const actionId of actionIds) {
            const action = builderActions.getAction(actionId);
            if (action && action.setPanel) {
                action.setPanel(this);
            }
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

    /**
     * Registers class-to-field mappings for save operations (shop only)
     */
    registerClassSaveMapping(classesOption, field) {
        if (!this.props.isShop) return;

        if (!this.classSaveMappings.has(field)) {
            this.classSaveMappings.set(field, new Map());
        }

        if (Array.isArray(classesOption)) {
            // BuilderRange, store the entire array
            this.classSaveMappings.get(field).set('__array__', {
                type: 'array',
                classes: classesOption
            });
        } else {
            // Single options, store as individual options
            if (!this.classSaveMappings.get(field).has('__options__')) {
                this.classSaveMappings.get(field).set('__options__', new Set());
            }
            this.classSaveMappings.get(field).get('__options__').add(classesOption || '');
        }
    }

    /**
     * Registers template mappings for view toggling (shop only)
     */
    registerTemplateMapping(templateClass, views) {
        if (!this.props.isShop || !templateClass) return;

        this.templateMappings.set(templateClass, {
            views: Array.isArray(views) ? views : [views]
        });
    }

    async toggleViews(views) {
        const websiteConfigAction = this.env.editor.shared.builderActions?.getAction('websiteConfig');

        try {
            return await websiteConfigAction.apply({
                editingElement: this.env.getEditingElement(),
                params: { views }
            });
        } catch (error) {
            console.warn(error);
        }
    }
}

/**
 * Metadata collector for options that need database persistence.
 * Delegates DOM manipulation to classAction/setClassRange while collecting metadata for save.
 */
class ClassActionWithSaveAction extends BuilderAction {
    static id = "classActionWithSave";
    static dependencies = ["builderActions"];

    setup() {
        SharedActionMethods.setupActions(this);
    }

    getPriority(context) {
        return SharedActionMethods.delegate(this, 'getPriority', context, context.params.className) || 0;
    }

    isApplied(context) {
        const result = SharedActionMethods.delegate(this, 'isApplied', context, context.params.className);
        return result !== undefined ? result : true;
    }

    getValue(context) {
        return SharedActionMethods.delegate(this, 'getValue', context, context.params.className);
    }

    apply(context) {
        const { editingElement, params: { className, suggestedClasses, saveField } } = context;

        // Register metadata for save operations (only for shop context)
        if (saveField && this.panel?.props.isShop) {
            this.panel.registerClassSaveMapping(className, saveField);
        }

        // Apply suggested classes first
        if (suggestedClasses) {
            this.applySuggestedClasses(editingElement, suggestedClasses);
        }

        // Delegate DOM manipulation to appropriate action
        return SharedActionMethods.delegate(this, 'apply', context, className);
    }

    clean(context) {
        const { editingElement, params: { className, suggestedClasses, saveField } } = context;

        // Clean suggested classes first (before main classes)
        if (suggestedClasses) {
            this.cleanSuggestedClasses(editingElement, suggestedClasses);
        }

        // Register metadata for save (shop only)
        if (saveField && this.panel?.props.isShop) {
            this.panel.registerClassSaveMapping(className, saveField);
        }

        // Delegate DOM manipulation to appropriate action
        return SharedActionMethods.delegate(this, 'clean', context, className);
    }

    setPanel(panel) {
        this.panel = panel;
    }

    /**
     * Applies suggested classes based on the suggestedClasses parameter.
     * Example: "alpha beta !gamma" will add 'alpha' and 'beta', remove 'gamma'
     */
    applySuggestedClasses(editingElement, suggestedClasses) {
        if (!suggestedClasses || typeof suggestedClasses !== 'string') { return; }

        const classTokens = suggestedClasses.trim().split(/\s+/).filter(Boolean);

        for (const token of classTokens) {
            if (token.startsWith('!')) {
                const classToRemove = token.substring(1);
                if (classToRemove) {
                    editingElement.classList.remove(classToRemove);
                }
            } else  if (token) {
                 editingElement.classList.add(token);
            }
        }
    }

    /**
     * Cleans suggested classes reversing applySuggestedClasses.
     */
    cleanSuggestedClasses(editingElement, suggestedClasses) {
        if (!suggestedClasses || typeof suggestedClasses !== 'string') { return; }

        const classTokens = suggestedClasses.trim().split(/\s+/).filter(Boolean);

        for (const token of classTokens) {
            if (token.startsWith('!')) {
                const classToAdd = token.substring(1);
                if (classToAdd) {
                    editingElement.classList.add(classToAdd);
                }
            } else if (token) {
                editingElement.classList.remove(token);
            }
        }
    }
}

/**
 * Metadata collector for template view toggling.
 */
class TemplateConfigAction extends BuilderAction {
    static id = "templateConfig";
    static dependencies = ["builderActions"];

    setup() {
        SharedActionMethods.setupActions(this);
    }

    getPriority(context) {
        return SharedActionMethods.delegate(this, 'getPriority', context, context.params.templateClass) || 0;
    }

    isApplied(context) {
        const result = SharedActionMethods.delegate(this, 'isApplied', context, context.params.templateClass);
        return result !== undefined ? result : true;
    }

    getValue(context) {
        return SharedActionMethods.delegate(this, 'getValue', context, context.params.templateClass);
    }

    apply(context) {
        const { params: { views, templateClass } } = context;

        // Register metadata for save (shop only)
        if (views && templateClass && this.panel?.props.isShop) {
            this.panel.registerTemplateMapping(templateClass, views);
        }

        // Delegate DOM manipulation to classAction
        return SharedActionMethods.delegate(this, 'apply', context, templateClass);
    }

    clean(context) {
        const { params: { views, templateClass } } = context;

        // Also register metadata during clean operations
        // This ensures mappings are registered even when options start in "off" state
        if (views && templateClass && this.panel?.props.isShop) {
            this.panel.registerTemplateMapping(templateClass, views);
        }

        // Delegate DOM manipulation to classAction
        return SharedActionMethods.delegate(this, 'clean', context, templateClass);
    }

    setPanel(panel) {
        this.panel = panel;
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
        if (this.panel?.props.isShop) {
            editingElement.dataset.gapToSave = value;
        }
    }

    setPanel(panel) {
        this.panel = panel;
    }
}

// Utility: shared methods object for reducing repetition
const SharedActionMethods = {
    setupActions(action) {
        action.classAction = action.dependencies.builderActions.getAction('classAction');
        action.setClassRangeAction = action.dependencies.builderActions.getAction('setClassRange');
    },

    delegate(action, method, context, mainParam) {
        const targetAction = Array.isArray(mainParam) ? action.setClassRangeAction : action.classAction;
        return targetAction[method]?.({ ...context, params: { mainParam } });
    }
};


// Register actions with the panel
ProductsDesignPanel.actions = {
    ClassActionWithSaveAction,
    TemplateConfigAction,
    SetGapAction,
};
