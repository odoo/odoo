import { ResCurrency } from "./mock_server/mock_models/res_currency";
import { accountModels } from "@account/../tests/account_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

export const accountInvoiceExtractModels = {
    ResCurrency,
};

export function defineAccountInvoiceExtractModels() {
    return defineModels({ ...accountModels, ...mailModels, ...accountInvoiceExtractModels });
}

/**
 * @param {Object} params
 * @param {string} params.fieldName
 * @param {integer} params.id
 * @param {integer} [params.page=0]
 * @param {boolean} params.ocr_selected
 * @param {boolean} params.user_selected
 */
function createBoxData(params) {
    return {
        text: params.text || "",
        box_angle: 0, // no angle
        box_height: 0.2, // 20% of the box layer for the height
        box_midX: 0.5, // box in the middle of box layer (horizontally)
        box_midY: 0.5, // box in the middle of box layer (vertically)
        box_width: 0.2, // 20% of the box layer of the width
        feature: params.fieldName,
        id: params.id,
        page: params.page || 0, // which box layer this box is linked to
        ocr_selected: params.ocr_selected,
        user_selected: params.user_selected,
    };
}

/**
 * Important: the field name of boxes should be compatible.
 * @see account_invoice_extract.Fields:init
 *
 * @returns {Object[]}
 */
export function createBoxesData() {
    const vatBoxes = [
        createBoxData({
            fieldName: "VAT_Number",
            id: 1,
            ocr_selected: false,
            user_selected: false,
        }),
        createBoxData({
            fieldName: "VAT_Number",
            id: 2,
            ocr_selected: true,
            user_selected: false,
            text: "BE0477472701",
        }),
        createBoxData({
            fieldName: "VAT_Number",
            id: 3,
            ocr_selected: false,
            user_selected: true,
        }),
    ];
    const invoiceIdBoxes = [
        createBoxData({
            fieldName: "invoice_id",
            id: 4,
            ocr_selected: false,
            user_selected: false,
        }),
        createBoxData({
            fieldName: "invoice_id",
            id: 5,
            ocr_selected: true,
            user_selected: true,
        }),
    ];
    const supplierBoxes = [
        createBoxData({
            fieldName: "supplier",
            id: 6,
            ocr_selected: false,
            user_selected: true,
        }),
        createBoxData({
            fieldName: "supplier",
            id: 7,
            ocr_selected: true,
            user_selected: false,
            text: "Some partner",
        }),
        createBoxData({
            fieldName: "supplier",
            id: 8,
            ocr_selected: false,
            user_selected: false,
        }),
    ];
    const totalBoxes = [
        createBoxData({
            fieldName: "total",
            id: 9,
            ocr_selected: true,
            user_selected: true,
        }),
        createBoxData({
            fieldName: "total",
            id: 10,
            ocr_selected: false,
            user_selected: false,
        }),
    ];
    const dateBoxes = [
        createBoxData({
            fieldName: "date",
            id: 11,
            ocr_selected: true,
            user_selected: true,
        }),
        createBoxData({
            fieldName: "date",
            id: 12,
            ocr_selected: false,
            user_selected: false,
        }),
        createBoxData({
            fieldName: "date",
            id: 13,
            ocr_selected: false,
            user_selected: false,
        }),
    ];
    const dueDateBoxes = [
        createBoxData({
            fieldName: "due_date",
            id: 14,
            ocr_selected: true,
            user_selected: false,
        }),
        createBoxData({
            fieldName: "due_date",
            id: 15,
            ocr_selected: false,
            user_selected: true,
        }),
    ];
    const currencyBoxes = [
        createBoxData({
            fieldName: "currency",
            id: 16,
            ocr_selected: true,
            user_selected: false,
        }),
        createBoxData({
            fieldName: "currency",
            id: 17,
            ocr_selected: false,
            user_selected: true,
        }),
    ];
    return [].concat(
        vatBoxes,
        invoiceIdBoxes,
        supplierBoxes,
        totalBoxes,
        dateBoxes,
        dueDateBoxes,
        currencyBoxes
    );
}
