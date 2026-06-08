import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";
import { props, t } from "@odoo/owl";

export class MassMailingBorderOption extends BaseOptionComponent {
    static id = "mass_mailing_border_option";
    static template = "mass_mailing.BorderOption";
    props = props({
        withRoundCorner: t.boolean().optional(true),
    });
}

registry.category("mass_mailing-options").add(MassMailingBorderOption.id, MassMailingBorderOption);
