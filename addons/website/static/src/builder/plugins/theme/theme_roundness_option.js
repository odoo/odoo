import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useCustomizedVariables } from "./utils";

export class ThemeRoundnessOption extends BaseOptionComponent {
    static template = "website.ThemeRoundnessOption";

    setup() {
        super.setup();
        this.state = useCustomizedVariables({
            // [grep: border-radius-multipliers] Same multipliers as the
            // $border-radius-sm/-lg fallbacks in website's
            // bootstrap_overridden.scss.
            "border-radius-sm": { derivedFrom: "border-radius", ratio: 0.75 },
            "border-radius-lg": { derivedFrom: "border-radius", ratio: 1.5 },
        });
    }
}
