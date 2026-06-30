import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Many2OneOption extends BaseOptionComponent {
    static template = "html_builder.Many2OneOption";
    static selector = "[data-oe-many2one-model]:not([data-oe-readonly])";
    static editableOnly = false;

    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(async () => {
            const el = this.env.getEditingElement();
            const contactOpts = JSON.parse(el.dataset.oeContactOptions || "{}");
            this.nullText = contactOpts.null_text;
            this.model = el.dataset.oeMany2oneModel;
            this.domain = JSON.parse(el.dataset.oeMany2oneDomain || "[]");
            const searchResult = await this.orm.searchRead(
                "ir.model",
                [["model", "=", this.model]],
                ["name"]
            );
            this.label = searchResult[0]?.name;
        });
    }
}
