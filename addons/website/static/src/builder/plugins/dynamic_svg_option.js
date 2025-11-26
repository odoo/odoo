import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class DynamicSvgOption extends BaseOptionComponent {
    static id = "dynamic_svg_option";
    static template = "website.DynamicSvgOption";

    setup() {
        super.setup();
        this.title = {
            c1: _t("Change primary color"),
            c2: _t("Change secondary color"),
            c3: _t("Change color"),
            c4: _t("Change accent color"),
            c5: _t("Change color"),
        };
        this.domState = useDomState((imgEl) => {
            const colors = {};
            const searchParams = new URL(imgEl.src, window.location.origin).searchParams;
            for (const colorName of ["c1", "c2", "c3", "c4", "c5"]) {
                const color = searchParams.get(colorName);
                if (color) {
                    colors[colorName] = color;
                }
            }
            return {
                colors: colors,
            };
        });
    }
}

registry.category("builder-options").add(DynamicSvgOption.id, DynamicSvgOption);
