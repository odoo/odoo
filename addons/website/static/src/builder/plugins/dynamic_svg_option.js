import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class DynamicSvgOption extends BaseOptionComponent {
    static template = "website.DynamicSvgOption";
    static props = {};

    setup() {
        super.setup();
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
