import BarcodeModel from "@stock_barcode/models/barcode_model";

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";


patch(BarcodeModel.prototype, {

     /**
     * The purpose of this extension is to allow the user to create the product for the barcode data
     * if no product found based on barcode lookup!
     *
     * @override
     */
    async noProductToast(barcodeData) {
        // Applicable for the group ["base.group_system"]
        // Applicable for models ["stock.picking", "stock.quant"]
        // Applicable for the picking operation ["receipts"]
        const canManageBarcodelookup = await this.groups.group_user_admin;
        if (
          canManageBarcodelookup && this.isValidForBarcodeLookup &&
          ["ean8", "ean13", "upca"].some((encoding) =>
            this.parser.check_encoding(barcodeData.barcode, encoding)
          )
        ) {
            this.trigger("playSound", "error");
            if (!barcodeData.error) {
                if (this.groups.group_tracking_lot) {
                    barcodeData.error = _t(
                        `This product doesn't exists either scan a package
                                available at the picking location or create new product`
                    );
                } else {
                    barcodeData.error = _t("This product doesn't exists");
                }
            }
            return this.notification(barcodeData.error, {
                type: "danger",
                buttons: [
                    {
                        name: _t("Create New Product"),
                        primary: true,
                        onClick: () => {
                            const notifications = registry
                                .category("main_components")
                                .get("NotificationContainer").props.notifications;
                            for (const id in notifications) {
                                const notification = notifications[id];
                                if (notification.onClose) {
                                    notification.onClose();
                                }
                                delete notifications[id];
                            }
                            return this.openProductForm(barcodeData);
                        },
                    },
                ],
            });
        }
        return super.noProductToast(barcodeData);
    },

    async openProductForm(barcodeData=false) {
        return await this.action.doAction(
            "stock_barcode_barcodelookup.stock_barcodelookup_product_product_action",
            {
                additionalContext: {
                    "default_barcode": barcodeData?.barcode,
                    "default_is_storable": true,
                    "dialog_size": "medium",
                    "skip_barcode_check": true,
                },
                props: {
                    onSave: async (record) => {
                        this.notification(_t("Product created successfully"), { type: "success" });
                        barcodeData ? await this.createNewProductLine(barcodeData) : false;
                        return this.action.doAction({ type: "ir.actions.act_window_close" });
                    },
                },
            }
        );
    },

    async createNewProductLine(barcodeData) {
        const barcodes_by_model = { "product.product": [barcodeData.barcode] };
        const params = { barcodes_by_model };
        try {
            const result = await rpc("/stock_barcode/get_specific_barcode_data", params);
            if (Object.keys(result).length === 0) {
                const message = _t("No record found for the specified barcode");
                return this.notification(message, {
                    title: _t("Inconsistent Barcode"),
                    type: "danger",
                });
            }
            this.cache.setCache(result);

            // modifying the barcodeData
            const [productRecord] = result["product.product"];
            barcodeData.match = true;
            barcodeData.quantity = 1;
            barcodeData.product = productRecord;
            const fieldsParams = this._convertDataToFieldsParams(barcodeData);
            if (barcodeData.uom) {
                fieldsParams.uom = barcodeData.uom;
            }
            const currentLine = await this.createNewLine({fieldsParams});
            if (currentLine) {
                this._selectLine(currentLine);
            }
            this.trigger("update");
            return true;
        } catch (error) {
            return this.notification(error, {
                title: _t("RPC Error"),
                type: "danger",
            });
        }
    }
});
