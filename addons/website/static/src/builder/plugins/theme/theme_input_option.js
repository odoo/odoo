import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useVariablesDifferentFromGlobal } from "../utils";

export class ThemeInputOption extends BaseOptionComponent {
    static template = "website.ThemeInputOption";

    setup() {
        super.setup();
        this.state = useVariablesDifferentFromGlobal(
            ["input-border-radius", "input-border-radius-sm", "input-border-radius-lg"],
            this.document
        );
    }
}
