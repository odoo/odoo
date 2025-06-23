import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/*
 * This plugin makes background layers border radius follow
 * the radius of their parent element.
 *
 * Example: if a div has border 50 and border-radius 60, its
 * child element containing the background should have radius
 * 60 (parent border-radius) - 50 (parent border) = 10
 *
 * It also works with multiple border or radius values, so an
 * element with border 20 30 40 10 and radius 50 80 60 70 will have
 * a child element with radius
 * 50 - max(20, 10) = 30
 * 80 - max(30, 20) = 50
 * 60 - max(40, 30) = 20
 * 70 - max(10, 40) = 30
 */
class BorderRadiusStylePlugin extends Plugin {
    static id = "borderRadiusStyle";
    resources = {
        step_added_handlers: () => {
            this.getChildBackgroundEls(this.document).forEach((element) => {
                this.calculateAndSetRadius(element);
            });
        },
    };

    calculateAndSetRadius(backgroundEl) {
        const parentElement = backgroundEl.parentElement;
        const parentRadius = this.getBorderValues(parentElement, "border-radius");
        const parentWidth = this.getBorderValues(parentElement, "border-width");
        backgroundEl.style.borderRadius = parentRadius
            .map(
                (radius, index) =>
                    Math.max(
                        0,
                        (radius || 0) -
                            Math.max(
                                parentWidth[index] || 0,
                                parentWidth[index === 0 ? 3 : index - 1] || 0
                            )
                    ) + "px"
            )
            .join(" ");
    }

    getChildBackgroundEls(element) {
        return element.querySelectorAll(".o_we_bg_filter, .s_parallax_bg");
    }

    getBorderValues(parentElement, styleName) {
        const borderValuesArray = this.window
            .getComputedStyle(parentElement)
            [styleName].split(" ")
            .map((val) => parseInt(val));

        switch (borderValuesArray.length) {
            case 0:
                borderValuesArray.push(0);
                break;
            case 1:
                borderValuesArray.push(
                    borderValuesArray[0],
                    borderValuesArray[0],
                    borderValuesArray[0]
                );
                break;
            case 2:
                borderValuesArray.push(borderValuesArray[0], borderValuesArray[1]);
                break;
            case 3:
                borderValuesArray.push(borderValuesArray[1]);
                break;
        }

        return borderValuesArray;
    }
}
registry.category("website-plugins").add(BorderRadiusStylePlugin.id, BorderRadiusStylePlugin);
