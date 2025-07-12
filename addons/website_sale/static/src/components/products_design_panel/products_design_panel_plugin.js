import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { ProductsDesignPanel } from "./products_design_panel";

export class ProductsDesignPanelPlugin extends Plugin {
    static id = "productsDesignPanel";
    static dependencies = ["builderActions", "builderComponents"];
    static shared = ["registerShopPanel", "unregisterShopPanel"];

    resources = {
        builder_actions: ProductsDesignPanel.actions,
        builder_components: {
            ProductsDesignPanel,
        },
        save_handlers: this.onSave.bind(this),
    };

    setup() {
        this.shopPanel = null;
    }

    registerShopPanel(panel) {
        if (!panel.props.isShop) {
            return;
        }
        this.shopPanel = panel;
    }

    unregisterShopPanel(panel) {
        if (this.shopPanel === panel) {
            this.shopPanel = null;
        }
    }

    async onSave() {
        // Only proceed if is shop...
        if (!this.shopPanel || !this.shopPanel.props.isShop) {
            return;
        }

        const pageEl = this.shopPanel.env.getEditingElement();

        // ...and if we have actual data to save
        if (this.shopPanel.classSaveMappings.size === 0 &&
            this.shopPanel.templateMappings.size === 0 &&
            !pageEl.dataset.gapToSave) {
            return;
        }

        const updateData = {};

        // Save gap
        if (pageEl.dataset.gapToSave !== undefined) {
            updateData.shop_gap = pageEl.dataset.gapToSave;
        }

        // Save classes by comparing DOM state with registered options
        for (const [field, fieldData] of this.shopPanel.classSaveMappings) {
            const currentClasses = Array.from(pageEl.classList);
            let matchedOption = '';

            // Check if this field has array-based options (from BuilderRange)
            if (fieldData.has('__array__')) {
                const arrayData = fieldData.get('__array__');
                const classArray = arrayData.classes;

                // Find which class from the array is currently applied
                for (let i = 0; i < classArray.length; i++) {
                    if (classArray[i] && currentClasses.includes(classArray[i])) {
                        matchedOption = classArray[i];
                        break;
                    }
                }
            }
            // Check if this field has individual options
            else if (fieldData.has('__options__')) {
                const options = Array.from(fieldData.get('__options__'));

                // Sort by complexity (longest combinations first)
                const sortedOptions = options.sort((a, b) => {
                    const aLength = String(a || '').split(' ').filter(Boolean).length;
                    const bLength = String(b || '').split(' ').filter(Boolean).length;
                    return bLength - aLength;
                });

                // Find which option matches the current DOM state
                for (const classOption of sortedOptions) {
                    const classStr = String(classOption || '');

                    if (classStr === '') {
                        // Empty option - check if no related classes are present
                        const hasAnyRelatedClass = sortedOptions.some(option => {
                            const optStr = String(option || '');
                            if (optStr === '') return false;
                            const optionClasses = optStr.includes(' ') ?
                                optStr.split(' ').filter(Boolean) : [optStr];
                            return optionClasses.some(cls => currentClasses.includes(cls));
                        });
                        if (!hasAnyRelatedClass) {
                            matchedOption = '';
                            break;
                        }
                    } else {
                        // Check if this option matches
                        const requiredClasses = classStr.includes(' ') ?
                            classStr.split(' ').filter(Boolean) : [classStr];

                        if (requiredClasses.every(cls => currentClasses.includes(cls))) {
                            matchedOption = classStr;
                            break;
                        }
                    }
                }
            }

            updateData[field] = matchedOption;
        }

        // Toggle templates by comparing DOM state with registered options
        const viewsToToggle = [];
        for (const [templateClass, { views }] of this.shopPanel.templateMappings) {
            const isActive = pageEl.classList.contains(templateClass);
            const viewsToProcess = isActive ? views : views.map(v => `!${v}`);
            viewsToToggle.push(...viewsToProcess);
        }

        if (viewsToToggle.length > 0) {
            await this.toggleViews(viewsToToggle);
        }

        // Save gap and data
        if (Object.keys(updateData).length > 0) {
            return rpc("/shop/config/website", updateData);
        }
    }

    async toggleViews(views) {
        const websiteConfigAction = this.shopPanel.env.editor.shared.builderActions?.getAction('websiteConfig');

        try {
            return await websiteConfigAction.apply({
                editingElement: this.shopPanel.env.getEditingElement(),
                params: { views }
            });
        } catch (error) {
            console.warn("[website_sale] toggle views failed:");
            console.warn(error);
        }
    }
}

registry.category("website-plugins").add(ProductsDesignPanelPlugin.id, ProductsDesignPanelPlugin);
