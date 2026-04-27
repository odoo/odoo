/** @odoo-module **/

import { Digipad } from '@stock_barcode/widgets/digipad';

import { patch } from "@web/core/utils/patch";

patch(Digipad.prototype, {
    get changes() {
        const changes = super.changes;
        if ( 'manual_consumption' in this.props.record.data ) {
            changes.manual_consumption = true;
        }
        return changes;
    }
});
