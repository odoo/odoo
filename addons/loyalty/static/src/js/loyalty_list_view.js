/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart } = owl;

export class LoyaltyActionHelper extends Component {
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
LoyaltyActionHelper.template = "loyalty.LoyaltyActionHelper";

export class LoyaltyListRenderer extends ListRenderer {};
LoyaltyListRenderer.template = "loyalty.LoyaltyListRenderer";
LoyaltyListRenderer.components = {
    ...LoyaltyListRenderer.components,
    LoyaltyActionHelper,
};

export const LoyaltyListView = {
    ...listView,
    Renderer: LoyaltyListRenderer,
};

registry.category("views").add("loyalty_program_list_view", LoyaltyListView);
