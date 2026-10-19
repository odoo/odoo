import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class HeaderNavigationOption extends BaseOptionComponent {
    static id = "header_navigation_option";
    static template = "website.HeaderNavigationOption";
    static dependencies = ["customizeWebsite", "headerOption"];

    setup() {
        super.setup();

        this.headerTemplates = this.dependencies.headerOption.getHeaderTemplates();
        this.headerTemplateIds = this.headerTemplates.map((template) => template.props.views[0]);
        this.currentActiveViews = {};
        onWillStart(async () => {
            this.currentActiveViews = await this.getCurrentActiveViews();
        });
    }

    hasSomeViews(views) {
        for (const view of views) {
            if (this.currentActiveViews[view]) {
                return true;
            }
        }
        return false;
    }
    async getCurrentActiveViews() {
        const actionParams = { views: this.headerTemplateIds };
        await this.dependencies.customizeWebsite.loadConfigKey(actionParams);
        const currentActiveViews = {};
        for (const key of this.headerTemplateIds) {
            const isActive = this.dependencies.customizeWebsite.getConfigKey(key);
            currentActiveViews[key] = isActive;
        }
        return currentActiveViews;
    }

    getAlignmentViews(direction) {
        if (!direction || direction === "left") {
            return [];
        }
        const views = [];
        // We find the active template, and make corresponding alignment views
        const activeTemplate = this.headerTemplates.find(
            (template) => this.currentActiveViews[template.props.views[0]]
        );
        if (activeTemplate) {
            const templateId = activeTemplate.props.views[0];
            const templateAlignment = activeTemplate.props.defaultAlignment;
            // If not alignment is set, then the default alignment is "desktop left"
            if (!templateAlignment || "desktop" in templateAlignment) {
                views.push(templateId + `_align_${direction}`);
            }
            if (templateAlignment && "mobile" in templateAlignment) {
                views.push(templateId + `_mobile_align_${direction}`);
            }
        }
        return views;
    }
}

registry.category("website-options").add(HeaderNavigationOption.id, HeaderNavigationOption);
