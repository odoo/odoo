import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Many2OneOption extends BaseOptionComponent {
    static template = "html_builder.Many2OneOption";
    static props = [];
    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(async () => {
            const el = this.env.getEditingElement();
            this.model = el.dataset.oeMany2oneModel;
            const searchResult = await this.orm.searchRead(
                "ir.model",
                [["model", "=", this.model]],
                ["name"]
            );
            this.label = searchResult[0]?.name;
        });
    }
}
