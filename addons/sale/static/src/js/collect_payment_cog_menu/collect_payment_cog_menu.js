import { Component, onWillStart } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useEnv } from "@web/owl2/utils";
import { ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * 'Collect Payment' Menu
 *
 * This menu offers the payment link on quotations, and both the payment link and the payment
 * registration on confirmed orders.
 */
export class CollectPaymentCogMenu extends Component {
    static template = "sale.CollectPaymentCogMenu";
    static components = { Dropdown, DropdownItem };

    setup() {
        this.action = useService("action");
        onWillStart(async () => {
            this.canRegisterPayment = await user.hasGroup("account.group_account_invoice");
        });
    }

    async openPaymentLinkWizard() {
        const record = this.env.model.root;
        if (await record.save()) {
            this.action.doAction("sale.action_sale_order_generate_link", {
                additionalContext: {
                    active_model: record.resModel,
                    active_id: record.resId,
                    active_ids: [record.resId],
                },
                onClose: () => record.load(),
            });
        }
    }

    async openRegisterPaymentWizard() {
        const record = this.env.model.root;
        if (await record.save()) {
            this.action.doActionButton({
                type: "object",
                name: "action_register_payment",
                resModel: record.resModel,
                resId: record.resId,
                onClose: () => record.load(),
            });
        }
    }
}

export const collectPaymentMenuItem = {
    Component: CollectPaymentCogMenu,
    groupNumber: ACTIONS_GROUP_NUMBER,
    isDisplayed() {
        const env = useEnv();
        return (
            env.searchModel.resModel === "sale.order"
            && env.config.viewType === "form"
            && !env.model.root.isNew
        );
    },
};

cogMenuRegistry.add("collect-payment-menu", collectPaymentMenuItem);
