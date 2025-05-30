/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;


// Fonction pour supprimer la classe 'selected' des lignes de commande
const removeSelectedClass = () => {
    const selectedOrderLines = document.querySelectorAll(".orderline.selected");
    selectedOrderLines.forEach(el => {
        el.classList.remove("selected");
    });
};
// Fonction pour désactiver les interactions sur les anciennes lignes de commande
const disableInteractionOnOldOrders = (orderLines, isAdmin) => {
    orderLines.forEach(line => {
        if (!isAdmin && line.classList.contains("orderline") && !line.classList.contains("text-success")) {
            // Désactiver le clic sur les anciennes lignes
            line.classList.remove("cursor-pointer");
            line.style.pointerEvents = "none";
            line.style.userSelect = "none";
            line.style.cursor = "not-allowed";

            // Désactiver l'UI du numpad (boutons de modification de quantité)
            const numpadButtons = document.querySelectorAll(".numpad button");
            numpadButtons.forEach(button => {
                button.disabled = true;
                button.style.pointerEvents = "none";
            });
        }
    });
};



patch(PosStore.prototype, {

    async setup() {
        console.log("setup store")

        await super.setup(...arguments);
    },

    getPrintingChanges(order, diningModeUpdate) {
        console.log("order", order);
        if (!order.ticket_number || order.ticket_number === 0) {
            const today = new Date();
            const todayString = today.toDateString();

            const lastResetDate = localStorage.getItem("pos.last_reset_date");
            const currentCounter = parseInt(localStorage.getItem("pos.ticket_number")) || 0;

            let newTicketNumber;

            if (lastResetDate !== todayString) {
                newTicketNumber = 1;
                localStorage.setItem("pos.ticket_number", "1");
                localStorage.setItem("pos.last_reset_date", todayString);
                console.log("🔄 Reset quotidien - Nouveau ticket #1");
            } else {
                newTicketNumber = currentCounter + 1;
                localStorage.setItem("pos.ticket_number", newTicketNumber.toString());
                console.log(`📝 Nouveau ticket #${newTicketNumber} pour aujourd'hui`);
            }

            order.ticket_number = newTicketNumber;
            this.ticket_number = newTicketNumber;

        } else {
            this.ticket_number = parseInt(order.ticket_number);
            console.log("♻️ Réutilisation ticket existant:", order.ticket_number);
        }

        const time = DateTime.now().toFormat("dd/MM/yyyy HH:mm");

        return {
            table_name: order.table_id ? order.table_id.table_number : "",
            floor_name: order.table_id?.floor_id.name || "",
            config_name: order.config.name,
            time: time,
            tracking_number: order.tracking_number,
            ticket_number: this.ticket_number,
            takeaway: order.config.takeaway && order.takeaway,
            employee_name: order.employee_id?.name || order.user_id?.name,
            order_note: order.general_note,
            diningModeUpdate: diningModeUpdate,
        };
    },
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.is_spanish = this.config.is_spanish;
        result.simplified_partner_id = this.config.simplified_partner_id.id;
        if (order) {
            result.is_l10n_es_simplified_invoice = order.is_l10n_es_simplified_invoice;
            result.partner = order.get_partner();
            result.invoice_name = order.invoice_name;
        }
        return result;
    },
     getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.ticket_number = order.ticket_number;
        return result;
    },
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        console.log("🟨 addLineToOrder called with vals:", vals);
        console.log("🟨 Initial opts:", opts);
        console.log("🔒 Check order isLocked ->", order.isLocked());

        let merge = true;
        order.assert_editable();

        const options = {
            ...opts,
        };

        if ("price_unit" in vals) {
            merge = false;
        }

        if (typeof vals.product_id == "number") {
            vals.product_id = this.data.models["product.product"].get(vals.product_id);
        }
        const product = vals.product_id;

        const values = {
            price_type: "price_unit" in vals ? "manual" : "original",
            price_extra: 0,
            price_unit: 0,
            order_id: this.get_order(),
            qty: 1,
            tax_ids: product.taxes_id.map((tax) => ["link", tax]),
            ...vals,
        };

        // Handle refund constraints
        if (
            order.doNotAllowRefundAndSales() &&
            order._isRefundOrder() &&
            (!values.qty || values.qty > 0)
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Refund and Sales not allowed"),
                body: _t("It is not allowed to mix refunds and sales"),
            });
            return;
        }

        // In case of configurable product a popup will be shown to the user
        // We assign the payload to the current values object.
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        if (values.product_id.isConfigurable() && configure) {
            const payload = await this.openConfigurator(values.product_id);

            if (payload) {
                const productFound = this.models["product.product"]
                    .filter((p) => p.raw?.product_template_variant_value_ids?.length > 0)
                    .find((p) =>
                        p.raw.product_template_variant_value_ids.every((v) =>
                            payload.attribute_value_ids.includes(v)
                        )
                    );

                Object.assign(values, {
                    attribute_value_ids: payload.attribute_value_ids
                        .filter((a) => {
                            if (productFound) {
                                const attr =
                                    this.data.models["product.template.attribute.value"].get(a);
                                return (
                                    attr.is_custom || attr.attribute_id.create_variant !== "always"
                                );
                            }
                            return true;
                        })
                        .map((id) => [
                            "link",
                            this.data.models["product.template.attribute.value"].get(id),
                        ]),
                    custom_attribute_value_ids: Object.entries(payload.attribute_custom_values).map(
                        ([id, cus]) => [
                            "create",
                            {
                                custom_product_template_attribute_value_id:
                                    this.data.models["product.template.attribute.value"].get(id),
                                custom_value: cus,
                            },
                        ]
                    ),
                    price_extra: values.price_extra + payload.price_extra,
                    qty: payload.qty || values.qty,
                    product_id: productFound || values.product_id,
                });
            } else {
                return;
            }
        } else if (values.product_id.product_template_variant_value_ids.length > 0) {
            // Verify price extra of variant products
            const priceExtra = values.product_id.product_template_variant_value_ids
                .filter((attr) => attr.attribute_id.create_variant !== "always")
                .reduce((acc, attr) => acc + attr.price_extra, 0);
            values.price_extra += priceExtra;
        }

        // In case of clicking a combo product a popup will be shown to the user
        // It will return the combo prices and the selected products
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        if (values.product_id.isCombo() && configure) {
            const payload = await makeAwaitable(this.dialog, ComboConfiguratorPopup, {
                product: values.product_id,
            });

            if (!payload) {
                return;
            }

            const comboPrices = computeComboItems(
                values.product_id,
                payload,
                order.pricelist_id,
                this.data.models["decimal.precision"].getAll(),
                this.data.models["product.template.attribute.value"].getAllBy("id")
            );

            values.combo_line_ids = comboPrices.map((comboItem) => [
                "create",
                {
                    product_id: comboItem.combo_item_id.product_id,
                    tax_ids: comboItem.combo_item_id.product_id.taxes_id.map((tax) => [
                        "link",
                        tax,
                    ]),
                    combo_item_id: comboItem.combo_item_id,
                    price_unit: comboItem.price_unit,
                    price_type: "automatic",
                    order_id: order,
                    qty: 1,
                    attribute_value_ids: comboItem.attribute_value_ids?.map((attr) => [
                        "link",
                        attr,
                    ]),
                    custom_attribute_value_ids: Object.entries(
                        comboItem.attribute_custom_values
                    ).map(([id, cus]) => [
                        "create",
                        {
                            custom_product_template_attribute_value_id:
                                this.data.models["product.template.attribute.value"].get(id),
                            custom_value: cus,
                        },
                    ]),
                },
            ]);
        }

        // In the case of a product with tracking enabled, we need to ask the user for the lot/serial number.
        // It will return an instance of pos.pack.operation.lot
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        const code = opts.code;
        let pack_lot_ids = {};
        if (values.product_id.isTracked() && (configure || code)) {
            const packLotLinesToEdit =
                (!values.product_id.isAllowOnlyOneLot() &&
                    this.get_order()
                        .get_orderlines()
                        .filter((line) => !line.get_discount())
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

        // In case of clicking a product with tracking weight enabled a popup will be shown to the user
        // It will return the weight of the product as quantity
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        if (values.product_id.to_weight && this.config.iface_electronic_scale && configure) {
            if (values.product_id.isScaleAvailable) {
                this.scale.setProduct(values.product_id, this.getProductPrice(values.product_id));
                const weight = await makeAwaitable(this.env.services.dialog, ScaleScreen);
                if (weight) {
                    values.qty = weight;
                } else {
                    return;
                }
            } else {
                await values.product_id._onScaleNotAvailable();
            }
        }

        // Handle price unit
        if (!values.product_id.isCombo() && vals.price_unit === undefined) {
            values.price_unit = values.product_id.get_price(order.pricelist_id, values.qty);
        }
        const isScannedProduct = opts.code && opts.code.type === "product";
        if (values.price_extra && !isScannedProduct) {
            const price = values.product_id.get_price(
                order.pricelist_id,
                values.qty,
                values.price_extra
            );

            values.price_unit = price;
        }

        // === CUSTOM LOCK LOGIC STARTS HERE ===
        console.log("🔍 Checking for existing lines...");

        // TOUJOURS forcer la création d'une nouvelle ligne - pas de merge
        console.log("🆕 Forcing new line creation - no merge allowed");
        merge = true; // Empêcher tout merge avec les lignes existantes

        // === CUSTOM LOCK LOGIC ENDS HERE ===

        const line = this.data.models["pos.order.line"].create({ ...values, order_id: order });
        line.setOptions(options);

        // Si la commande est verrouillée, marquer la nouvelle ligne
        if (order.isLocked()) {
            console.log("🔒 Marking new line as created after lock");
            line.created_after_lock = true;
            line.locked = true; // Optionnel : verrouiller immédiatement
        }

        this.selectOrderLine(order, line);
        if (configure) {
            this.numberBuffer.reset();
        }
        const selectedOrderline = order.get_selected_orderline();
        if (options.draftPackLotLines && configure) {
            selectedOrderline.setPackLotLines({
                ...options.draftPackLotLines,
                setQuantity: options.quantity === undefined,
            });
        }
        console.log("selected order lines",selectedOrderline);

        let to_merge_orderline;
        for (const curLine of order.lines) {
            if (curLine.id !== line.id) {
                // Modification : ne pas merger avec des lignes verrouillées
                console.log("curLine",curLine.isLocked());
                if (curLine.can_be_merged_with(line) && merge !== false && !curLine.locked) {
                    to_merge_orderline = curLine;
                    console.log("🔄 Will merge with existing unlocked line");
                }
            }
        }


        if (to_merge_orderline) {
            to_merge_orderline.merge(line);
            line.delete();
            this.selectOrderLine(order, to_merge_orderline);
            console.log("✅ Successfully merged with existing line");
        } else if (!selectedOrderline) {
            this.selectOrderLine(order, order.get_last_orderline());
            console.log("🆕 Created new line (no merge possible)");
        }

        if (product.tracking === "serial") {
            this.selectedOrder.get_selected_orderline().setPackLotLines({
                modifiedPackLotLines: pack_lot_ids.modifiedPackLotLines ?? [],
                newPackLotLines: pack_lot_ids.newPackLotLines ?? [],
                setQuantity: true,
            });
        }
        if (configure) {
            this.numberBuffer.reset();
        }

        // FIXME: Put this in an effect so that we don't have to call it manually.
        order.recomputeOrderData();

        if (configure) {
            this.numberBuffer.reset();
        }

        this.hasJustAddedProduct = true;
        clearTimeout(this.productReminderTimeout);
        this.productReminderTimeout = setTimeout(() => {
            this.hasJustAddedProduct = false;
        }, 3000);

        // FIXME: If merged with another line, this returned object is useless.
        return line;
    },


    async showLoginScreen() {
        this.showScreen("FloorScreen");
        this.reset_cashier();
        this.showScreen("LoginScreen");
        this.dialog.closeAll();
    }


});