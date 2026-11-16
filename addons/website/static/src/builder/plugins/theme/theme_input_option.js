import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useCustomizedVariables } from "./utils";

export class ThemeInputOption extends BaseOptionComponent {
    static template = "website.ThemeInputOption";

    setup() {
        super.setup();
        this.state = useCustomizedVariables({
            "input-border-radius": { derivedFrom: "border-radius" },
            "input-border-radius-sm": { derivedFrom: "border-radius-sm" },
            "input-border-radius-lg": { derivedFrom: "border-radius-lg" },
        });
    }
}
