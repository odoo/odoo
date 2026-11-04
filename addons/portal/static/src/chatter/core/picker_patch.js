import { Picker } from "@mail/core/common/picker";

import { patch } from "@web/core/utils/patch";

patch(Picker.prototype, {
    get popoverSettings() {
        const settings = super.popoverSettings;
        settings.fixedPosition = false;
        return settings;
    },
});
