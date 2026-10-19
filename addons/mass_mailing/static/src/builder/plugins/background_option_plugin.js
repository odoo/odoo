import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";
import { registry } from "@web/core/registry";
import { t } from "@odoo/owl";

export class MailingBackgroundOption extends BackgroundOption {
    static id = "mailing_background_option";
    // withShapes inlined from BackgroundOption.props (still old-style)
    static propShape = {
        withColors: t.boolean().optional(false),
        withImages: t.boolean().optional(true),
        withColorCombinations: t.boolean().optional(false),
        withShapes: t.boolean().optional(),
    };
}

registry.category("mass_mailing-options").add(MailingBackgroundOption.id, MailingBackgroundOption);
