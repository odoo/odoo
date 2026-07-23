import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class PortalListColumnsOption extends BaseOptionComponent {
    static id = "portal_list_columns_option";
    static template = "website.PortalListColumnsOption";
    static dependencies = ["portalListOption"];

    setup() {
        super.setup();
        this.state = proxy({ columnChoices: "[]" });
        onWillStart(async () => {
            // The option is bound to `main` (selector); the table it configures
            // is reached through the same applyTo the BuilderList uses.
            const tableEl = this.env.getEditingElement().querySelector("table[data-list-ref]");
            if (!tableEl) {
                return;
            }
            this.state.columnChoices = JSON.stringify(
                await this.dependencies.portalListOption.loadColumns(tableEl)
            );
        });
    }
}

registry.category("website-options").add(PortalListColumnsOption.id, PortalListColumnsOption);
