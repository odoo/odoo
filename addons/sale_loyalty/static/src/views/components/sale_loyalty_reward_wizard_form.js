import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";


export class SaleLoyaltyRewardWizardFormController extends FormController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.env.dialogData.dismiss = () => this.discard();
    }

    async discard() {
        if (this.props.context?.coupon_code?.length > 0) {
            // FIX ME: this.props.resId is always false, so though the method is called, we get empty object at python side
            await this.orm.call(
                "sale.loyalty.reward.wizard",
                "action_discard",
                [this.props.resId],
                {
                    context: this.props.context,
                }
            );
        }
        this.env.dialogData.close();
    }
}

export const form = { ...formView, Controller: SaleLoyaltyRewardWizardFormController };

registry.category("views").add("sale_loyalty_reward_wizard_form", form);
