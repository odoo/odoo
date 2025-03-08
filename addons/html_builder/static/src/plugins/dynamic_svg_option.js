import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../core/default_builder_components";
import { useDomState } from "@html_builder/core/building_blocks/utils";

export class DynamicSvgOption extends Component {
    static template = "html_builder.DynamicSvgOption";
    static components = { ...defaultBuilderComponents };
    static props = {};

    setup() {
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
