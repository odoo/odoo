import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onMounted, signal } from "@odoo/owl";

export class ThemeShadowOption extends BaseOptionComponent {
    static template = "website.ThemeShadowOption";
    rootRef = signal(null);

    setup() {
        super.setup();
        this.shadowSizeToShow = this.env.shadowSizeToShow;

        onMounted(() => {
            if (this.shadowSizeToShow) {
                this.rootRef().scrollIntoView({ behavior: "instant", block: "center" });
            }
        });
    }
}
