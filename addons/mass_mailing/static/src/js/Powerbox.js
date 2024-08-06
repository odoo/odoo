/** @odoo-module **/

import { Powerbox } from "@web_editor/js/editor/odoo-editor/src/powerbox/Powerbox";
import { patch } from "@web/core/utils/patch";

patch(Powerbox.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.commands = this.commands.filter(command => command.name !== 'Checklist');
    }
});
