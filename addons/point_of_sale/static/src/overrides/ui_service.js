import { patch } from "@web/core/utils/patch";
import { SIZES, utils } from "@web/ui/block/ui_service";
patch(utils, {
    isSmall(ui = {}) {
        return (ui.size || utils.getSize()) <= SIZES.MD;
    },
});
