/* @odoo-module */

import { useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { GifPicker } from "@mail/discuss/gif_picker/common/gif_picker";
import { PickerContent } from "@mail/core/common/picker_content";

Object.assign(PickerContent.components, { GifPicker });

patch(PickerContent.prototype, {
    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.gifPickerService = useState(useService("discuss.gifPicker"));
    },
});
