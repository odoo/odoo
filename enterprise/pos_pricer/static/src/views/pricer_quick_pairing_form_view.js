/** @odoo-module */
import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const PRICER_TAG_ID_LENGTH = 17;

export class PricerQuickPairingForm extends FormController {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.lastProductFound = null;

        useEffect(() => {
            const inputDumProdBarcode = document.getElementById("dummy_prod_barcode_0");
            const inputDumTagBarcode = document.getElementById("dummy_tag_barcode_0");

            if (!inputDumProdBarcode || !inputDumTagBarcode) {
                return;
            }

            // Handlers
            const productBarcodeFocusoutHandler = async (event) => {
                const productBarcode = event.target.value;
                if (!productBarcode) {
                    return;
                }

                const product = await this.orm.searchRead(
                    "product.product",
                    [["barcode", "=", productBarcode]],
                    ["id", "display_name"]
                );

                if (product.length) {
                    this.lastProductFound = product[0];
                    inputDumTagBarcode.focus();
                    this.notification.add(
                        _t("Product '%s' found", this.lastProductFound.display_name),
                        {
                            type: "success",
                        }
                    );
                } else {
                    this.lastProductFound = null;
                    inputDumProdBarcode.focus();
                    this.notification.add(_t("No product found for barcode '%s'", productBarcode), {
                        type: "warning",
                    });
                    this.model.root.update({ dummy_prod_barcode: "" });
                }
            };

            const productBarcodeKeydownHandler = (event) => {
                if (event.key === "Enter" && event.target.value) {
                    inputDumProdBarcode.blur();
                }
            };

            const tagBarcodeFocusoutHandler = async (event) => {
                const pricerTagBarcode = event.target.value;
                if (!pricerTagBarcode || !inputDumProdBarcode.value || !this.lastProductFound) {
                    return;
                } else if (
                    !(
                        // Check tag id validity in js to avoid ValidationError popup
                        // Should be 1 letter followed by 16 digits
                        // Example: N4081315789813275
                        (
                            pricerTagBarcode.length === PRICER_TAG_ID_LENGTH &&
                            isNaN(pricerTagBarcode[0]) &&
                            !isNaN(pricerTagBarcode.substring(1))
                        )
                    )
                ) {
                    this.notification.add(
                        _t(
                            "Invalid tag name. Should be 1 letter followed by 16 digits. Example: 'N4081315789813275'",
                            pricerTagBarcode
                        ),
                        {
                            type: "warning",
                        }
                    );
                    this.model.root.update({ dummy_tag_barcode: "" });
                    return;
                }

                const tag = await this.orm.searchRead(
                    "pricer.tag",
                    [["name", "=", pricerTagBarcode]],
                    ["id", "display_name"]
                );

                await this.orm.write("product.product", [this.lastProductFound.id], {
                    pricer_store_id: this.model.root.resId,
                });

                if (tag.length) {
                    this.notification.add(_t("Tag '%s' found", tag[0].display_name), {
                        type: "success",
                    });
                    await this.orm.write("pricer.tag", [tag[0].id], {
                        product_id: this.lastProductFound.id,
                    });
                } else {
                    this.notification.add(_t("Tag '%s' not found, creating it", pricerTagBarcode), {
                        type: "warning",
                    });
                    await this.orm.create("pricer.tag", [
                        {
                            name: pricerTagBarcode,
                            product_id: this.lastProductFound.id,
                        },
                    ]);
                }

                this.notification.add(
                    _t(
                        "Tag '%s' successfully linked with product '%s'",
                        pricerTagBarcode,
                        this.lastProductFound.display_name
                    ),
                    {
                        type: "success",
                    }
                );
                await this.model.load();
                inputDumProdBarcode.focus();
            };

            const tagBarcodeKeydownHandler = (event) => {
                if (event.key === "Enter" && event.target.value) {
                    inputDumTagBarcode.blur();
                }
            };

            // =========== ADD EVENT LISTENERS ===========
            inputDumProdBarcode.addEventListener("focusout", productBarcodeFocusoutHandler);
            inputDumProdBarcode.addEventListener("keydown", productBarcodeKeydownHandler);
            inputDumTagBarcode.addEventListener("focusout", tagBarcodeFocusoutHandler);
            inputDumTagBarcode.addEventListener("keydown", tagBarcodeKeydownHandler);

            return () => {
                // Remove the listeners at the end so they don't multiply
                inputDumProdBarcode.removeEventListener("focusout", productBarcodeFocusoutHandler);
                inputDumProdBarcode.removeEventListener("keydown", productBarcodeKeydownHandler);
                inputDumTagBarcode.removeEventListener("focusout", tagBarcodeFocusoutHandler);
                inputDumTagBarcode.removeEventListener("keydown", tagBarcodeKeydownHandler);
            };
        });
    }

    async save(params) {
        if (!this.lastProductFound) {
            this.model.root.dummy_prod_barcode = false;
            this.model.root.dummy_tag_barcode = false;
        }
        return await super.save(params);
    }
}

registry.category("views").add("pricer_quick_pairing_form", {
    ...formView,
    Controller: PricerQuickPairingForm,
});
