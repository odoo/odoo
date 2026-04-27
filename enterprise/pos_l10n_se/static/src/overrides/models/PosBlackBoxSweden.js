import { PosStore } from "@point_of_sale/app/store/pos_store";
import { SwedenBlackboxError } from "@pos_l10n_se/app/errors/error_handlers";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
const { DateTime } = luxon;

patch(PosStore.prototype, {
    useBlackBoxSweden() {
        return !!this.config.iface_sweden_fiscal_data_module;
    },
    disallowLineQuantityChange() {
        const result = super.disallowLineQuantityChange(...arguments);
        return this.useBlackBoxSweden() || result;
    },
    async preSyncAllOrders(orders) {
        if (this.useBlackBoxSweden() && orders.length > 0) {
            for (const order of orders) {
                await this.pushSingleOrder(order);
            }
        }
        return super.preSyncAllOrders(orders);
    },
    async pushSingleOrder(order) {
        if (this.useBlackBoxSweden() && order) {
            if (!order.receipt_type) {
                order.receipt_type = "normal";
                order.sequence_number = await this.get_order_sequence_number();
            }
            try {
                order.sweden_blackbox_tax_category_a = order.get_specific_tax(25);
                order.sweden_blackbox_tax_category_b = order.get_specific_tax(12);
                order.sweden_blackbox_tax_category_c = order.get_specific_tax(6);
                order.sweden_blackbox_tax_category_d = order.get_specific_tax(0);
                const data = await this.pushOrderToSwedenBlackbox(order);
                const result = data.result ?? data;
                if (result.error && result.error.errorCode != "000000") {
                    throw result.error;
                }
                this.setDataForPushOrderFromSwedenBlackBox(order, result);
            } catch (err) {
                order.state = "draft";
                throw new SwedenBlackboxError(err?.status?.message_title ?? err?.status ?? err);
            }
        }
    },
    async pushOrderToSwedenBlackbox(order) {
        const fdm = this.hardwareProxy.deviceControllers.fiscal_data_module;
        const data = {
            date: new DateTime(order.date_order).toFormat("yyyyMMddHHmm"),
            receipt_id: order.sequence_number.toString(),
            pos_id: this.config.id.toString(),
            organisation_number: this.company.company_registry.replace(/\D/g, ""),
            receipt_total: order.get_total_with_tax().toFixed(2).toString().replace(".", ","),
            negative_total:
                order.get_total_with_tax() < 0
                    ? Math.abs(order.get_total_with_tax()).toFixed(2).toString().replace(".", ",")
                    : "0,00",
            receipt_type: order.receipt_type,
            vat1: order.sweden_blackbox_tax_category_a
                ? "25,00;" + order.sweden_blackbox_tax_category_a.toFixed(2).replace(".", ",")
                : " ",
            vat2: order.sweden_blackbox_tax_category_b
                ? "12,00;" + order.sweden_blackbox_tax_category_b.toFixed(2).replace(".", ",")
                : " ",
            vat3: order.sweden_blackbox_tax_category_c
                ? "6,00;" + order.sweden_blackbox_tax_category_c.toFixed(2).replace(".", ",")
                : " ",
            vat4: order.sweden_blackbox_tax_category_d
                ? "0,00;" + order.sweden_blackbox_tax_category_d.toFixed(2).replace(".", ",")
                : " ",
        };

        return new Promise((resolve, reject) => {
            fdm.addListener((data) =>
                data.status === "ok" || data.status === "success" ? resolve(data) : reject(data)
            );
            fdm.action({
                action: "registerReceipt",
                high_level_message: data,
            }).then((response) => {
                if (!response.result) {
                    reject(_t("Blackbox is disconnected"));
                }
            });
        });
    },
    setDataForPushOrderFromSwedenBlackBox(order, data) {
        order.sweden_blackbox_signature = data.signature_control;
        order.sweden_blackbox_unit_id = data.unit_id;
    },
    async get_order_sequence_number() {
        return await this.data.call("pos.config", "get_order_sequence_number", [this.config.id]);
    },
    async get_profo_order_sequence_number() {
        return await this.data.call("pos.config", "get_profo_order_sequence_number", [
            this.config.id,
        ]);
    },
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.posIdentifier = this.config.name;
        if (order && this.useBlackBoxSweden()) {
            result.receipt_type = order.receipt_type;
            result.blackboxDate = order.blackbox_date;
            result.isReprint = order.isReprint;
            result.orderSequence = order.sequence_number;
            if (order.isReprint) {
                result.type = "COPY";
            } else if (order.isProfo) {
                result.type = "PRO FORMA";
            } else {
                result.type = (order.amount_total < 0 ? "return" : "") + "receipt";
            }
        }
        return result;
    },
});
