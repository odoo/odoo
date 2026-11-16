import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useCustomizedVariables } from "./utils";

export class ThemeCardOption extends BaseOptionComponent {
    static template = "website.ThemeCardOption";

    setup() {
        super.setup();
        this.state = useCustomizedVariables({
            "card-border-radius": { derivedFrom: "border-radius" },
        });
    }
}
