import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";
import { registry } from "@web/core/registry";

export class MailingBackgroundOption extends BackgroundOption {
    static id = "mailing_background_option";
    static props = {
        ...BackgroundOption.props,
        withColors: { type: Boolean, optional: true },
        withImages: { type: Boolean, optional: true },
        withColorCombinations: { type: Boolean, optional: true },
    };
    static defaultProps = {
        withImages: true,
        withColors: false,
        withColorCombinations: false,
    };
}

registry.category("builder-options").add(MailingBackgroundOption.id, MailingBackgroundOption);
