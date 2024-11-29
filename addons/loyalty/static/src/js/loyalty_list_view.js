import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";

export class LoyaltyActionHelper extends Component {
    static template = "loyalty.LoyaltyActionHelper";
    static props = ["noContentHelp"];
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        onWillStart(async () => {
            this.loyaltyTemplateData = await this.orm.call(
                "loyalty.program",
                "get_program_templates",
                [],
                {
                    context: this.env.model.root.context,
                },
            );
        });
    }

    async onTemplateClick(templateId) {
        const action = await this.orm.call(
            "loyalty.program",
            "create_from_template",
            [templateId],
            {context: this.env.model.root.context},
        );
        if (!action) {
            return;
        }
        this.action.doAction(action);
    }
};

export class LoyaltyListRenderer extends ListRenderer {
    static template = "loyalty.LoyaltyListRenderer";
    static components = {
        ...LoyaltyListRenderer.components,
        LoyaltyActionHelper,
    };
};

export const LoyaltyListView = {
    ...listView,
    Renderer: LoyaltyListRenderer,
};

registry.category("views").add("loyalty_program_list_view", LoyaltyListView);
