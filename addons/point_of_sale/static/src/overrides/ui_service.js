import { SIZES, utils } from "@web/core/ui/ui_utils";
import { patch } from "@web/core/utils/patch";

patch(utils, {
    isSmall(ui = {}) {
        return (ui.size?.() || utils.getSize()) <= SIZES.MD;
    },
});
