import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class MegaMenuOption extends BaseOptionComponent {
    static template = "website.MegaMenuOption";
    static props = {
        getTemplatePrefix: Function,
    };

    setup() {
        super.setup();
        this.state = useDomState((el) => ({
            templatePrefix: this.props.getTemplatePrefix(el),
        }));
    }
}
