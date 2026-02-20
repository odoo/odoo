import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import { formatCurrency } from "@web/core/currency";
import {
    changesToOrder,
    filterChangeByCategories,
    getStrNotes,
} from "../../models/utils/order_change";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;
/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
export class GeneratePrinterData {
    constructor() {
        this.setup(...arguments);
    }

    setup({ models, order = false, basicReceipt = false }) {
        this.models = models;
        this.order = order;
        this.basicReceipt = basicReceipt;
    }

    get config() {
        return this.models["pos.config"].getFirst();
    }

    get currency() {
        return this.config.currency_id;
    }

    get company() {
        return this.config.company_id;
    }

    get commonExtraData() {
        return {
            company_state_name: this.company.state_id?.name || "",
            company_country_name: this.company.country_id?.name || "",
            vat_label: this.company.country_id.vat_label || "Tax ID",
        };
    }

    formatCurrency(amount) {
        return formatCurrency(amount, this.currency.id);
    }

    /**
     * Methods bellow are used to generate sale details tickets data
     */
    generateSaleDetailsData(saleDetails) {
        const processData = (products) => {
            const productsByCategory = [];
            for (const productCat of products) {
                const products = productCat.products.reduce((acc, product) => {
                    if (!acc[product.product_id]) {
                        acc[product.product_id] = {
                            name: product.product_name,
                            quantity: 0,
                            total_paid: 0,
                        };
                    }

                    acc[product.product_id].quantity += product.quantity;
                    acc[product.product_id].total_paid += product.total_paid;
                    return acc;
                }, {});
                const productsList = Object.values(products).map((product) => ({
                    ...product,
                    total_paid: this.formatCurrency(product.total_paid),
                }));

                productsByCategory.push({
                    category_name: productCat.name,
                    total_quantity: productCat.qty,
                    products: productsList,
                    total: this.formatCurrency(productCat.total),
                });
            }

            return productsByCategory;
        };

        const processedPayments = saleDetails.payments.map((payment) => ({
            ...payment,
            total: this.formatCurrency(payment.total),
        }));

        const processedTaxes = saleDetails.taxes.map((tax) => ({
            ...tax,
            tax_amount: this.formatCurrency(tax.tax_amount),
        }));

        return {
            company: this.company.raw,
            config: this.config.raw,
            image: {
                logo: this.config.receiptLogoUrl,
            },
            extra_data: {
                ...this.commonExtraData,
                total_paid: this.formatCurrency(saleDetails.currency.total_paid),
                taxes: processedTaxes,
                sold: processData(saleDetails.products),
                refund: processData(saleDetails.refund_products),
                payments: processedPayments,
            },
        };
    }

    /**
     * Methods bellow are used to generate tip tickets data
     */
    generateTipData(name) {
        return {
            company: this.company.raw,
            order: this.order.raw,
            config: this.config.raw,
            image: {
                logo: this.config.receiptLogoUrl,
            },
            extra_data: {
                ...this.commonExtraData,
                date: new Date().toLocaleString(),
                prices: this.generateTaxData(),
                name: name || "",
            },
        };
    }

    /**
     * Methods bellow are used to generate cash move tickets data
     */
    generateCashMoveData({ reason, translatedType, formattedAmount, date }) {
        return {
            company: this.company.raw,
            config: this.config.raw,
            order: this.order.raw,
            image: {
                logo: this.config.receiptLogoUrl,
            },
            extra_data: {
                ...this.commonExtraData,
                reason: reason,
                translated_type: translatedType.toUpperCase(),
                formatted_amount: formattedAmount,
                date: new Date().toLocaleString(),
            },
        };
    }

    /**
     * Methods bellow are used to generate receipts tickets data
     */
    generateTaxData() {
        const data = this.order._constructPriceData();
        const discount = this.order.getTotalDiscount();
        const rounding = this.order.appliedRounding;

        return {
            same_tax_base: data.taxDetails.same_tax_base,
            discount_amount: discount ? this.formatCurrency(discount) : false,
            rounding_amount: rounding ? this.formatCurrency(rounding) : false,
            tax_amount: this.formatCurrency(data.taxDetails.tax_amount),
            total_amount: this.formatCurrency(data.taxDetails.total_amount),
            subtotal_amount: this.formatCurrency(data.taxDetails.base_amount_currency),
            taxes: data.taxDetails.subtotals[0]?.tax_groups?.map((tax) => ({
                name: tax.group_name,
                amount: this.formatCurrency(tax.tax_amount),
                amount_base: this.formatCurrency(tax.base_amount_currency),
            })),
        };
    }

    generateQrCode(value) {
        if (!value) {
            return null;
        }
        return generateQRCodeDataUrl(value);
    }

    generateLineData() {
        return this.order.lines.map((line) => {
            const productData = { ...line.product_id.raw };
            productData.display_name = line.getFullProductName();

            return {
                ...line.raw,
                product_data: productData,
                product_uom_name: line.product_id.uom_id?.name || "",
                unit_price: line.currencyDisplayPriceUnit,
                product_unit_price: line.product_id.displayPriceUnit,
                price_subtotal_incl: line.currencyDisplayPrice,
                lot_names: line.pack_lot_ids?.length
                    ? line.pack_lot_ids.map((l) => l.lot_name)
                    : false,
            };
        });
    }

    generatePaymentData() {
        return this.order.payment_ids.map((line) => ({
            ...line.raw,
            payment_method_data: { name: line.payment_method_id?.name || "" },
            amount: this.formatCurrency(line.amount),
        }));
    }

    generateReceiptData() {
        const baseUrl = this.config._base_url;
        const company = this.company;
        const url = `${baseUrl}/pos/ticket?order_uuid=${this.order.uuid}`;
        const useQrCode = company.point_of_sale_ticket_portal_url_display_mode !== "url";
        const useTips = this.config.set_tip_after_payment && this.order.displayPrice > 0;
        const tipPercentages = [
            this.config.tip_percentage_1,
            this.config.tip_percentage_2,
            this.config.tip_percentage_3,
        ];
        const tipsConfiguration = useTips
            ? tipPercentages.map((p) => [
                  `${p}%`,
                  this.formatCurrency(this.order.displayPrice * (p / 100)),
              ])
            : false;

        return {
            order: this.order.raw,
            config: this.config.raw,
            company: this.company.raw,
            partner: this.order.partner_id ? this.order.partner_id.raw : false,
            preset: this.order.preset_id ? this.order.preset_id.raw : false,
            lines: this.generateLineData(),
            payments: this.generatePaymentData(),
            image: {
                invoice_qr_code: useQrCode ? this.generateQrCode(url) : false,
                logo: this.config.receiptLogoUrl,
            },
            conditions: {
                basic_receipt: this.basicReceipt,
                display_vat: this.config._IS_VAT,
                display_qr_code: useQrCode,
                display_url: company.point_of_sale_ticket_portal_url_display_mode != "qr_code",
                use_self_invoicing: company.point_of_sale_use_ticket_qr_code,
                module_pos_restaurant: this.config.module_pos_restaurant,
            },
            extra_data: {
                ...this.commonExtraData,
                partner_vat_label: this.order.partner_id?.country_id?.vat_label || "Tax ID",
                tips_configuration: useTips ? tipsConfiguration : false,
                preset_datetime: this.order.presetDateTime,
                self_invoicing_url: `${baseUrl}/pos/ticket`,
                prices: this.generateTaxData(),
                cashier_name: this.order.getCashierName(),
                formated_date_order: this.order.formatDateOrTime("date_order", "datetime"),
                formated_shipping_date: this.order.formatDateOrTime("shipping_date", "date"),
            },
        };
    }

    /**
     * Methods bellow are used to generate preparations tickets data
     */
    preparePreparationGroupedData(changes) {
        const dataChanges = changes.data || [];
        if (dataChanges && dataChanges.some((c) => c.group)) {
            const groupedData = dataChanges.reduce((acc, c) => {
                const { name = "", index = -1 } = c.group || {};
                if (!acc[name]) {
                    acc[name] = { name, index, data: [] };
                }
                acc[name].data.push(c);
                return acc;
            }, {});
            changes.groupedData = Object.values(groupedData).sort((a, b) => a.index - b.index);
        }
        return changes;
    }

    generatePreparationChanges(orderChange, categoryIdsSet) {
        const isPartOfCombo = (line) =>
            line.isCombo ||
            line.combo_parent_uuid ||
            this.models["product.product"].get(line.product_id).type == "combo";
        const comboChanges = orderChange.new.filter(isPartOfCombo);
        const normalChanges = orderChange.new.filter((line) => !isPartOfCombo(line));
        normalChanges.sort((a, b) => {
            const sequenceA = a.pos_categ_sequence;
            const sequenceB = b.pos_categ_sequence;
            if (sequenceA === 0 && sequenceB === 0) {
                return a.pos_categ_id - b.pos_categ_id;
            }

            return sequenceA - sequenceB;
        });
        orderChange.new = [...comboChanges, ...normalChanges];
        return filterChangeByCategories(categoryIdsSet, orderChange, this.models);
    }

    generatePreparationReceipts(orderChange, categoryIdsSet) {
        const changes = this.generatePreparationChanges(orderChange, categoryIdsSet);
        const receiptsData = [];
        if (changes.new.length) {
            receiptsData.push(
                this.preparePreparationGroupedData({
                    title: _t("NEW"),
                    data: changes.new,
                })
            );
        }

        if (changes.cancelled.length) {
            receiptsData.push(
                this.preparePreparationGroupedData({
                    title: _t("CANCELLED"),
                    data: changes.cancelled,
                })
            );
        }

        if (changes.noteUpdate.length) {
            const { noteUpdateTitle, printNoteUpdateData = true } = orderChange;
            receiptsData.push(
                this.preparePreparationGroupedData({
                    title: noteUpdateTitle || _t("NOTE UPDATE"),
                    data: printNoteUpdateData ? changes.noteUpdate : [],
                })
            );
        }

        if (orderChange.internal_note || orderChange.general_customer_note) {
            receiptsData.push(this.preparePreparationGroupedData({ title: "", data: [] }));
        }
        return receiptsData;
    }

    generatePreparationData(categoryIdsSet, opts = { orderChange: null }) {
        const order = this.order;
        const override = opts.orderChange;
        let orderChange = override || changesToOrder(this.order, categoryIdsSet, opts.cancelled);
        let reprint = false;

        if (
            !orderChange.new.length &&
            !orderChange.cancelled.length &&
            !orderChange.noteUpdate.length &&
            !orderChange.internal_note &&
            !orderChange.general_customer_note &&
            order.uiState.lastPrints
        ) {
            orderChange = [order.uiState.lastPrints.at(-1)];
            reprint = true;
        } else {
            order.uiState.lastPrints.push(orderChange);
            orderChange = [orderChange];
        }

        if (reprint && opts.orderDone) {
            return [];
        }

        const receipts = [];
        const changes = orderChange.filter(Boolean);
        for (const change of changes) {
            const data = this.generatePreparationReceipts(change, categoryIdsSet);

            for (const changeData of data) {
                receipts.push({
                    changes: changeData,
                    order: order.raw,
                    config: this.config.raw,
                    company: this.company.raw,
                    partner: order.partner_id ? order.partner_id.raw : false,
                    preset: order.preset_id ? order.preset_id.raw : false,
                    extra_data: {
                        ...this.commonExtraData,
                        reprint: Boolean(reprint),
                        time: DateTime.now().toFormat("HH:mm"),
                        internal_note: getStrNotes(change.internal_note) || false,
                        general_customer_note: orderChange.general_customer_note || false,
                        employee_name: order.employee_id?.name || order.user_id?.name || false,
                        preset_time: order.presetDateTime || false,
                    },
                    conditions: {
                        module_pos_restaurant: this.config.module_pos_restaurant,
                    },
                });
            }
        }

        return receipts;
    }
}
