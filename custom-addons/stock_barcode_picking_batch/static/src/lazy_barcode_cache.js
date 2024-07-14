/** @odoo-module **/

import LazyBarcodeCache from '@stock_barcode/lazy_barcode_cache';

import { patch } from "@web/core/utils/patch";

patch(LazyBarcodeCache.prototype, {
    /**
     * @override
     */
     _constructor() {
        super._constructor(...arguments);
        this.barcodeFieldByModel['stock.picking.batch'] = 'name';
    },
});
