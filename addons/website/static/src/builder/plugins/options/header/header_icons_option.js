import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class HeaderIconsOption extends BaseOptionComponent {
    static id = "header_icons_option";
    static template = "website.HeaderIconsOption";

    setup() {
        super.setup();
        const labels = this.getResource("header_icon_labels");
        this.state = useDomState((editingElement) => {
            const names = new Set(
                [...editingElement.querySelectorAll("[data-header-icon]")].map(
                    (iconEl) => iconEl.dataset.headerIcon
                )
            );
            return {
                icons: labels
                    .filter(({ name }) => names.has(name))
                    .map(({ name, label }) => ({ name, label: label.toString() })),
            };
        });
    }
}

registry.category("website-options").add(HeaderIconsOption.id, HeaderIconsOption);
