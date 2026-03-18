import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class HeaderNavigationOption extends BaseOptionComponent {
    static id = "header_navigation_option";
    static template = "website.HeaderNavigationOption";
    static dependencies = ["customizeWebsite"];

    setup() {
        super.setup();

        this.headerTemplates = this.getResource("header_templates_providers")
            .flatMap((provider) => provider())
            .map((template) => `website.template_header_` + template.key);
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
        const actionParams = { views: this.headerTemplates };
        await this.dependencies.customizeWebsite.loadConfigKey(actionParams);
        const currentActiveViews = {};
        for (const key of this.headerTemplates) {
            const isActive = this.dependencies.customizeWebsite.getConfigKey(key);
            currentActiveViews[key] = isActive;
        }
        return currentActiveViews;
    }

    getAlignmentView(direction) {
        if (!direction || direction === "left") {
            return [];
        }
        // We find the active template, and make a corresponding alignment view
        return this.headerTemplates
            .filter((view) => this.currentActiveViews[view])
            .map((template) => template + `_align_${direction}`);
    }
}

registry.category("website-options").add(HeaderNavigationOption.id, HeaderNavigationOption);
