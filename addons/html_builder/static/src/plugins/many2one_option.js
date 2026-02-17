import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class Many2OneOption extends BaseOptionComponent {
    static id = "many2one_option";
    static template = "html_builder.Many2OneOption";
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

registry.category("builder-options").add(Many2OneOption.id, Many2OneOption);
