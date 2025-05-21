import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Many2OneOption extends BaseOptionComponent {
    static template = "website_builder.Many2OneOption";
    static props = [];
    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(async () => {
            const el = this.env.getEditingElement();
            this.model = el.dataset.oeMany2oneModel;
            [{ name: this.label }] = await this.orm.searchRead(
                "ir.model",
                [["model", "=", this.model]],
                ["name"]
            );
        });
    }
}
