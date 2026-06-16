import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useVariablesDifferentFromGlobal } from "../utils";

export class ThemeCardOption extends BaseOptionComponent {
    static template = "website.ThemeCardOption";

    setup() {
        super.setup();
        this.state = useVariablesDifferentFromGlobal(["card-border-radius"], this.document);
    }
}
