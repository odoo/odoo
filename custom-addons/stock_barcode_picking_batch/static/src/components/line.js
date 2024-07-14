/** @odoo-module **/

import LineComponent from '@stock_barcode/components/line';
import { patch } from "@web/core/utils/patch";


patch(LineComponent.prototype, {

    get componentClasses() {
        return [
            super.componentClasses,
            this.line.colorLine !== undefined ? 'o_colored_markup' : ''
        ].join(' ');
    }

});
