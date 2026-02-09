import { useRef } from "@web/owl2/utils";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { onMounted } from "@odoo/owl";

export class ThemeShadowOption extends BaseOptionComponent {
    static template = "website.ThemeShadowOption";

    setup() {
        super.setup();
        this.shadowSizeToShow = this.env.shadowSizeToShow;
        const root = useRef("root");

        onMounted(() => {
            if (this.shadowSizeToShow) {
                root.el.scrollIntoView({ behavior: "instant", block: "center" });
            }
        });
    }
}
