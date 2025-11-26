import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class MassMailingBorderOption extends BaseOptionComponent {
    static id = "mass_mailing_border_option";
    static template = "mass_mailing.BorderOption";
    static props = {
        withRoundCorner: { type: Boolean, optional: true },
    };
    static defaultProps = {
        withRoundCorner: true,
    };
}

registry.category("mass_mailing-options").add(MassMailingBorderOption.id, MassMailingBorderOption);
