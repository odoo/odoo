import { Plugin } from "@html_editor/plugin";
import { setElementToMaxZindex } from "@html_builder/builder/utils/grid_layout_utils";
import { isMobileView } from "@html_builder/builder/utils/utils";

const gridItemSelector = ".row.o_grid_mode > div.o_grid_item";

function isGridItem(el) {
    return el.matches(gridItemSelector);
}

export class GridLayoutPlugin extends Plugin {
    static id = "gridLayout";
    static dependencies = ["overlay", "history"];
    resources = {
        get_overlay_buttons: this.getActiveOverlayButtons.bind(this),
    };

    setup() {
        this.target = null;
    }

    getActiveOverlayButtons(target) {
        if (!isGridItem(target)) {
            this.target = null;
            return [];
        }

        const buttons = [];
        this.target = target;
        if (!isMobileView(this.target)) {
            buttons.push(
                {
                    class: "o_send_back",
                    handler: this.sendGridItemToBack.bind(this, "prev"),
                },
                {
                    class: "o_bring_front",
                    handler: this.bringGridItemToFront.bind(this, "next"),
                }
            );
        }
        return buttons;
    }

    sendGridItemToBack() {
        const rowEl = this.target.parentNode;
        const columnEls = [...rowEl.children].filter((el) => el !== this.target);
        const minZindex = Math.min(...columnEls.map((el) => el.style.zIndex));

        // While the minimum z-index is not 0, it is OK to decrease it and to
        // set the column to it. Otherwise, the column is set to 0 and the
        // other columns z-index are increased by one.
        if (minZindex > 0) {
            this.target.style.zIndex = minZindex - 1;
        } else {
            columnEls.forEach((columnEl) => columnEl.style.zIndex++);
            this.target.style.zIndex = 0;
        }
        this.dependencies.history.addStep();
    }

    bringGridItemToFront() {
        const rowEl = this.target.parentNode;
        setElementToMaxZindex(this.target, rowEl);
        this.dependencies.history.addStep();
    }
}
