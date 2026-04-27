import { patch } from "@web/core/utils/patch";
import { GenericHooks } from "@point_of_sale/../tests/tours/utils/generic_hooks";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import { session } from "@web/session";

patch(GenericHooks, {
    _receiptContains(elementClass, value) {
        const elSelector = `.receipt-screen .pos-receipt .${elementClass}`;
        return [
            {
                content: `Find ${elementClass} element`,
                trigger: elSelector,
            },
            {
                content: `Check ${elementClass} element contents`,
                trigger: `${elSelector}:contains("${value}")`,
            },
        ].flat();
    },
    _receiptContainsRegex(elementClass, regex) {
        const elSelector = `.receipt-screen .pos-receipt .${elementClass}`;
        return [
            {
                content: `Find ${elementClass} element`,
                trigger: elSelector,
            },
            {
                content: `Check ${elementClass} element contents`,
                trigger: elSelector,
                run: function () {
                    const el = document.querySelector(elSelector);

                    if (!regex.test(el.innerText)) {
                        throw new Error(
                            `Content of element '${elSelector}' does not match '${regex}'`
                        );
                    }
                },
            },
        ].flat();
    },
    afterValidateHook(...args) {
        const company_name =
            session.user_companies.allowed_companies[session.user_companies.current_company].name;

        if (company_name === "Company CO") {
            return [
                ReceiptScreen.isShown(),
                ReceiptScreen.receiptIsThere(),

                // Header
                this._receiptContains(
                    "receipt_header_l10n_co_edi_type",
                    "Factura Electrónica de Venta"
                ),
                this._receiptContains(
                    "receipt_header_l10n_co_edi_document_number",
                    "Número de Documento: SETF990000001"
                ),
                this._receiptContains(
                    "receipt_header_l10n_co_edi_authorization_number",
                    "DIAN resolution: 18760000001"
                ),
                this._receiptContains(
                    "receipt_header_l10n_co_edi_date_range",
                    "Fecha efectiva desde 2020-01-19 a 2030-01-19"
                ),
                this._receiptContains(
                    "receipt_header_l10n_co_edi_sequence_range",
                    "990000000 a 995000000"
                ),
                this._receiptContains(
                    "receipt_header_l10n_co_edi_payment_option",
                    "Metodo de Pago: Crédito ACH"
                ),
                this._receiptContains(
                    "receipt_header_l10n_co_edi_payment_option_code",
                    "Termino de Pago: Crédito"
                ),

                // Before footer
                this._receiptContains(
                    "receipt_l10n_co_edi_partner_name",
                    "Razón social / Nombre: AAAA Generic Partner"
                ),
                this._receiptContains(
                    "receipt_l10n_co_edi_identification_type",
                    "Tipo de identificación: Cédula de ciudadanía"
                ),
                this._receiptContains(
                    "receipt_l10n_co_edi_identification_number",
                    "Número de identificación: 222222222222"
                ),
                this._receiptContains("receipt_l10n_co_edi_address", "Dirección: Colombia"),
                this._receiptContains(
                    "receipt_l10n_co_edi_large_taxpayer",
                    "No Somos Grandes Contribuyentes"
                ),
                this._receiptContains("receipt_l10n_co_edi_fiscal_regimen", "Regimen fiscal: IVA"),
                this._receiptContains(
                    "receipt_l10n_co_edi_obligation_type_description",
                    "Régimen Simple de Tributación – SIMPLE"
                ),

                // After footer
                this._receiptContainsRegex(
                    "receipt_l10n_co_edi_signing_time",
                    /^Fecha de firma: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2})?$/
                ),
                this._receiptContainsRegex(
                    "receipt_l10n_co_edi_issue_date_time",
                    /^Fecha de emisión: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2})?$/
                ),
                this._receiptContains(
                    "receipt_l10n_co_edi_pos_serial_number",
                    "Número de serie del punto de venta: SN000001"
                ),
            ].flat();
        }

        return super.afterValidateHook(...args);
    },
});
