import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { SelectLotPopup } from "@pos_stock/app/components/popups/select_lot_popup/select_lot_popup";
import { makeAwaitable, ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

const { DateTime } = luxon;
export const CONSOLE_COLOR = "#F5B427";

patch(PosStore.prototype, {
    async processServerData() {
        this.pickingType = this.data.models["stock.picking.type"].getFirst();
        await super.processServerData();
    },

    async handleOrderLineConfiguration(order, values, code, vals, options, configure) {
        if ((configure || code) && values.product_tmpl_id.isTracked()) {
            const pack_lot_ids = await this.configureNewOrderLine(
                values.product_tmpl_id,
                vals,
                values,
                order,
                options,
                configure
            );
            if (!pack_lot_ids) {
                return false;
            }
            return pack_lot_ids;
        }
        return super.handleOrderLineConfiguration(...arguments);
    },

    processOrderlineConfiguration(order, values, extraConfig) {
        const selectedOrderline = order.getSelectedOrderline();
        if (values.product_id.tracking === "lot") {
            const productTemplate = values.product_id.product_tmpl_id;
            const related_lines = [];
            const price = productTemplate.getPrice(
                order.pricelist_id,
                values.qty,
                values.price_extra,
                false,
                values.product_id,
                selectedOrderline,
                related_lines
            );
            related_lines
                .filter((line) => line.price_type !== "manual")
                .forEach((line) => line.setUnitPrice(price));
        } else if (values.product_id.tracking === "serial") {
            selectedOrderline.setPackLotLines({
                modifiedPackLotLines: extraConfig.modifiedPackLotLines ?? [],
                newPackLotLines: extraConfig.newPackLotLines ?? [],
                setQuantity: true,
            });
        }

        return super.processOrderlineConfiguration(...arguments);
    },

    async configureNewOrderLine(productTemplate, vals, values, order, opts = {}, configure = true) {
        // In the case of a product with tracking enabled, we need to ask the user for the lot/serial number.
        // It will return an instance of pos.pack.operation.lot
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        const code = opts.code;
        let pack_lot_ids = {};
        if (values.product_tmpl_id.isTracked() && (configure || code)) {
            const packLotLinesToEdit =
                (!values.product_tmpl_id.isAllowOnlyOneLot() &&
                    this.getOrder()
                        .getOrderlines()
                        .filter((line) => !line.getDiscount())
                        .find((line) => line.product_id.id === values.product_id.id)
                        ?.getPackLotLinesToEdit()) ||
                [];

            // if the lot information exists in the barcode, we don't need to ask it from the user.
            if (code && code.type === "lot") {
                // consider the old and new packlot lines
                const modifiedPackLotLines = Object.fromEntries(
                    packLotLinesToEdit.filter((item) => item.id).map((item) => [item.id, item.text])
                );
                const newPackLotLines = [{ lot_name: code.code }];
                pack_lot_ids = { modifiedPackLotLines, newPackLotLines };
            } else {
                pack_lot_ids = await this.editLots(values.product_id, packLotLinesToEdit);
            }

            if (!pack_lot_ids) {
                return;
            } else {
                const packLotLine = pack_lot_ids.newPackLotLines;
                values.pack_lot_ids = packLotLine.map((lot) => ["create", lot]);
            }
        }
        return pack_lot_ids;
    },

    createNewOrder(data = {}) {
        data = {
            ...data,
            picking_type_id: this.pickingType,
        };
        return super.createNewOrder(data);
    },

    async pay() {
        const currentOrder = this.getOrder();
        if (
            currentOrder.lines.some(
                (line) =>
                    ["lot", "serial"].includes(line.getProduct().tracking) &&
                    !line.hasValidProductLot()
            ) &&
            (this.pickingType.use_create_lots || this.pickingType.use_existing_lots)
        ) {
            const confirmed = await ask(this.env.services.dialog, {
                title: _t("Some Serial/Lot Numbers are missing"),
                body: _t(
                    "You are trying to sell products with serial/lot numbers, but some of them are not set.\nWould you like to proceed anyway?"
                ),
            });
            if (confirmed) {
                this.mobile_pane = "right";
                this.navigate("PaymentScreen", {
                    orderUuid: this.selectedOrderUuid,
                });
            }
        } else {
            return super.pay(...arguments);
        }
    },

    async editLotsRefund(line) {
        const product = line.getProduct();
        const packLotLinesToEdit = line.pack_lot_ids.map((p) => ({
            id: p.id,
            text: p.lot_name,
        }));
        const alreadyRefundedLots = line.refunded_orderline_id.refund_orderline_ids
            .filter((item) => !["cancel", "draft"].includes(item.order_id.state))
            .flatMap((item) => item.pack_lot_ids)
            .map((p) => p.lot_name);
        const options = line.refunded_orderline_id.pack_lot_ids
            .map((p) => ({ id: p.id, name: p.lot_name, product_qty: line.qty }))
            .filter((lot) => !alreadyRefundedLots.includes(lot.name));
        const payload = await makeAwaitable(this.dialog, SelectLotPopup, {
            title: _t("Lot/Serial number(s) required for"),
            name: product.display_name,
            isSingleItem: product.isAllowOnlyOneLot(),
            array: packLotLinesToEdit,
            options: options,
            customInput: false,
            uniqueValues: product.tracking === "serial",
            isLotNameUsed: () => false,
        });
        if (payload) {
            const modifiedPackLotLines = {};
            const newPackLotLines = [];
            for (const item of payload) {
                if (item.id) {
                    modifiedPackLotLines[item.id] = item.text;
                } else {
                    newPackLotLines.push({ lot_name: item.text });
                }
            }
            return { modifiedPackLotLines, newPackLotLines };
        } else {
            return null;
        }
    },

    showNotificationIfLotExpired(lotName, lotExpDate = null) {
        const lotExpDateTime = deserializeDateTime(lotExpDate);
        if (lotExpDateTime.isValid && lotExpDateTime.ts <= DateTime.now().ts) {
            this.notification.add(_t("Lot/Serial %s is expired", lotName));
        }
    },

    async editLots(product, packLotLinesToEdit) {
        const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
        let canCreateLots = this.pickingType.use_create_lots || !this.pickingType.use_existing_lots;

        let existingLots = [];
        try {
            existingLots = await this.data.call("pos.order.line", "get_existing_lots", [
                this.company.id,
                this.config.id,
                product.id,
            ]);
            if (!canCreateLots && (!existingLots || existingLots.length === 0)) {
                this.dialog.add(AlertDialog, {
                    title: _t("No existing serial/lot number"),
                    body: _t(
                        "There is no serial/lot number for the selected product, and their creation is not allowed from the Point of Sale app."
                    ),
                });
                return null;
            }
        } catch (ex) {
            logPosMessage("Store", "editLots", "Collecting existing lots failed", CONSOLE_COLOR, [
                ex,
            ]);
            const confirmed = await ask(this.dialog, {
                title: _t("Server communication problem"),
                body: _t(
                    "The existing serial/lot numbers could not be retrieved. \nContinue without checking the validity of serial/lot numbers ?"
                ),
                confirmLabel: _t("Yes"),
                cancelLabel: _t("No"),
            });
            if (!confirmed) {
                return null;
            }
            canCreateLots = true;
        }

        const usedLotsQty = this.models["pos.pack.operation.lot"]
            .filter(
                (lot) =>
                    lot.pos_order_line_id?.product_id?.id === product.id &&
                    lot.pos_order_line_id?.order_id?.state === "draft"
            )
            .reduce((acc, lot) => {
                if (!acc[lot.lot_name]) {
                    acc[lot.lot_name] = { total: 0, currentOrderCount: 0 };
                }
                acc[lot.lot_name].total += lot.pos_order_line_id?.qty || 0;

                if (lot.pos_order_line_id?.order_id?.id === this.selectedOrder.id) {
                    acc[lot.lot_name].currentOrderCount += lot.pos_order_line_id?.qty || 0;
                }
                return acc;
            }, {});

        // Remove lot/serial names that are already used in draft orders
        existingLots = existingLots.filter(
            (lot) => lot.product_qty > (usedLotsQty[lot.name]?.total || 0)
        );

        // Check if the input lot/serial name is already used in another order
        const isLotNameUsed = (itemValue) => {
            const totalQty = existingLots.find((lt) => lt.name == itemValue)?.product_qty || 0;
            const usedQty = usedLotsQty[itemValue]
                ? usedLotsQty[itemValue].total - usedLotsQty[itemValue].currentOrderCount
                : 0;
            return usedQty ? usedQty >= totalQty : false;
        };

        const existingLotsName = existingLots.map((l) => l.name);
        if (!packLotLinesToEdit.length && existingLotsName.length === 1) {
            if (existingLots[0].expiration_date) {
                this.showNotificationIfLotExpired(
                    existingLots[0].name,
                    existingLots[0].expiration_date
                );
            }
            // If there's only one existing lot/serial number, automatically assign it to the order line
            return { newPackLotLines: [{ lot_name: existingLotsName[0] }] };
        }
        const payload = await makeAwaitable(this.dialog, SelectLotPopup, {
            title: _t("Lot/Serial number(s) required for"),
            name: product.display_name,
            isSingleItem: isAllowOnlyOneLot,
            array: packLotLinesToEdit,
            options: existingLots,
            customInput: canCreateLots,
            uniqueValues: product.tracking === "serial",
            isLotNameUsed: isLotNameUsed,
        });
        if (payload) {
            for (const item of payload) {
                if (!item.expiration_date) {
                    continue;
                }
                this.showNotificationIfLotExpired(item.text, item.expiration_date);
            }
            // Segregate the old and new packlot lines
            const modifiedPackLotLines = Object.fromEntries(
                payload.filter((item) => item.id).map((item) => [item.id, item.text])
            );
            const newPackLotLines = payload
                .filter((item) => !item.id)
                .map((item) => ({ lot_name: item.text }));

            return { modifiedPackLotLines, newPackLotLines };
        }
        return null;
    },
});
