/** @odoo-module **/

import {useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {CommandPalette} from "@web/core/commands/command_palette";
import {patch} from "@web/core/utils/patch";

export const unpatchCommandPalette = patch(CommandPalette.prototype, {
    setup() {
        super.setup();
        this.ui = useState(useService("ui"));
    },

    get small() {
        return this.ui.size < 2;
    },

    get contentClass() {
        return `o_command_palette ${this.small ? "" : "mt-5"}`;
    },
});
