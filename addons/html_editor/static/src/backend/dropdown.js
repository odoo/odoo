import { patch } from "@web/core/utils/patch";
import { Dropdown } from "@web/core/dropdown/dropdown";

patch(Dropdown.prototype, {
    getPopoverOptions() {
        const options = super.getPopoverOptions();
        if (this.isBottomSheet) {
            Object.assign(options, {
                withUnfocus: true,
            });
        }
        return options;
    },
});
