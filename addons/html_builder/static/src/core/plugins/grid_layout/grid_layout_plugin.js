import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { setElementToMaxZindex } from "@html_builder/utils/grid_layout_utils";
import { isMobileView } from "@html_builder/utils/utils";

const gridItemSelector = ".row.o_grid_mode > div.o_grid_item";

function isGridItem(el) {
    return el.matches(gridItemSelector);
}

export class GridLayoutPlugin extends Plugin {
    static id = "gridLayout";
    static dependencies = ["history"];
    resources = {
        get_overlay_buttons: withSequence(0, this.getActiveOverlayButtons.bind(this)),
    };

    setup() {
        this.overlayTarget = null;
    }

    getActiveOverlayButtons(target) {
        if (!isGridItem(target)) {
            this.overlayTarget = null;
            return [];
        }

        const buttons = [];
        this.overlayTarget = target;
        if (!isMobileView(this.overlayTarget)) {
            buttons.push(
                {
                    class: "o_send_back",
                    title: _t("Send to back"),
                    handler: this.sendGridItemToBack.bind(this),
                },
                {
                    class: "o_bring_front",
                    title: _t("Bring to front"),
                    handler: this.bringGridItemToFront.bind(this),
                }
            );
        }
        return buttons;
    }

    sendGridItemToBack() {
        const rowEl = this.overlayTarget.parentNode;
        const columnEls = [...rowEl.children].filter((el) => el !== this.overlayTarget);
        const minZindex = Math.min(...columnEls.map((el) => el.style.zIndex));

        // While the minimum z-index is not 0, it is OK to decrease it and to
        // set the column to it. Otherwise, the column is set to 0 and the
        // other columns z-index are increased by one.
        if (minZindex > 0) {
            this.overlayTarget.style.zIndex = minZindex - 1;
        } else {
            columnEls.forEach((columnEl) => columnEl.style.zIndex++);
            this.overlayTarget.style.zIndex = 0;
        }
    }

    bringGridItemToFront() {
        const rowEl = this.overlayTarget.parentNode;
        setElementToMaxZindex(this.overlayTarget, rowEl);
    }
}
