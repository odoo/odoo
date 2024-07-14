/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { patch } from "@web/core/utils/patch";
import { serializeDateTime } from "@web/core/l10n/dates";
const { DateTime } = luxon;

function getFormattedDate(value) {
    // convert to noon to avoid most timezone issues
    const date = DateTime.fromJSDate(value).set({ hours: 12, minutes: 0, seconds: 0 });
    return serializeDateTime(date);
}

patch(BarcodePickingModel.prototype, {

    async updateLine(line, args) {
        super.updateLine(...arguments);
        if (args.expiration_date) {
            line.expiration_date = args.expiration_date;
        }
    },

    async _processGs1Data(data) {
        const result = {};
        const { rule, value } = data;
        if (rule.type === 'expiration_date') {
            result.expirationDate = getFormattedDate(value);
            result.match = true;
        } else if (rule.type === 'use_date') {
            result.useDate = value;
            result.match = true;
        } else {
            return await super._processGs1Data(...arguments);
        }
        return result;
    },

    async _parseBarcode(barcode, filters) {
        const barcodeData = await super._parseBarcode(...arguments);
        const {product, useDate, expirationDate} = barcodeData;
        if (product && useDate && !expirationDate) {
            const value = new Date(useDate);
            value.setDate(useDate.getDate() + product.use_time);
            barcodeData.expirationDate = getFormattedDate(value);
        }
        return barcodeData;
    },

    _convertDataToFieldsParams(args) {
        const params = super._convertDataToFieldsParams(...arguments);
        if (args.expirationDate) {
            params.expiration_date = args.expirationDate;
        }
        return params;
    },

    _getFieldToWrite() {
        const fields = super._getFieldToWrite(...arguments);
        fields.push('expiration_date');
        return fields;
    },

    _createCommandVals(line) {
        const values = super._createCommandVals(...arguments);
        values.expiration_date = line.expiration_date;
        return values;
    },
});
