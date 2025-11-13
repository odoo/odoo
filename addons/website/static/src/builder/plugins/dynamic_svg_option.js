import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

export class DynamicSvgOption extends BaseOptionComponent {
    static template = "website.DynamicSvgOption";
    static selector = "img[src^='/html_editor/shape/'], img[src^='/web_editor/shape/']";

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
