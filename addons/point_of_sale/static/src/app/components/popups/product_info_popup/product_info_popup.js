import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useEffect, useState } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { serializeDateTime } from "@web/core/l10n/dates";
import { SnoozeDialog } from "./snooze_dialog/snooze_dialog";

const { DateTime } = luxon;

export class ProductInfoPopup extends Component {
    static template = "point_of_sale.ProductInfoPopup";
    static components = { Dialog, SnoozeDialog };
    static props = ["info", "productTemplate", "close"];

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.state = useState({
            countdown: "",
            activeSnooze: this.getActiveSnooze(),
        });

        useEffect(
            () => {
                if (!this.state.activeSnooze) {
                    return;
                }

                this.updateCountdown();
                const interval = setInterval(() => {
                    this.updateCountdown();
                }, 1000);
                return () => {
                    clearInterval(interval);
                };
            },
            () => [this.state.activeSnooze]
        );
    }
    searchProduct(productName) {
        this.pos.setSelectedCategory(0);
        this.pos.searchProductWord = productName;
        this.props.close();
    }
    _hasMarginsCostsAccessRights() {
        if (!this.pos.config.is_margins_costs_accessible_to_every_user) {
            return false;
        }
        return ["manager", "cashier"].includes(this.pos.getCashier()._role);
    }
    editProduct() {
        this.pos.editProduct(this.props.productTemplate);
        this.props.close();
    }
    get allowProductEdition() {
        return true; // Overrided in pos_hr
    }
    toggleFavorite() {
        this.pos.data.write("product.template", [this.props.productTemplate.id], {
            is_favorite: !this.props.productTemplate.is_favorite,
        });
    }
    get vatLabel() {
        return this.pos.company.country_id.vat_label || _t("VAT");
    }
    updateCountdown() {
        if (!this.state.activeSnooze) {
            return;
        }
        const now = DateTime.now();
        const endTime = this.state.activeSnooze.end_time;
        if (!endTime) {
            this.state.countdown = _t("Next session");
            return;
        }
        const diff = endTime.diff(now, ["hours", "minutes", "seconds"]);
        if (diff.as("seconds") <= 0) {
            this.state.countdown = "";
            this.state.activeSnooze = undefined;
            return;
        }

        this.state.countdown = diff.toFormat("hh:mm:ss");
        if (!this.ui.isSmall) {
            this.state.countdown = _t("%s left", this.state.countdown);
        }
    }
    async snooze(hours) {
        const start_time = DateTime.now();
        const end_time = hours ? serializeDateTime(start_time.plus({ hours: hours })) : null;
        const snooze = {
            start_time: serializeDateTime(start_time),
            end_time: end_time,
            pos_config_id: this.pos.config.id,
            product_template_id: this.props.productTemplate.id,
        };

        this.state.activeSnooze = (
            await this.pos.data.create("pos.product.template.snooze", [snooze])
        )[0];
    }
    openSnoozeDialog() {
        if (this.state.activeSnooze) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Stop Snooze"),
                body: _t(
                    "Do you want to stop the snooze early and make the product available again immediately?"
                ),
                confirmLabel: _t("Yes"),
                confirm: () => {
                    this.pos.data.delete("pos.product.template.snooze", [
                        this.state.activeSnooze.id,
                    ]);
                    this.state.activeSnooze = undefined;
                    this.state.countdown = "";
                },
                confirmClass: "btn-primary flex-grow-1 flex-sm-grow-0",
                cancelLabel: _t("Cancel"),
                cancel: () => {},
            });
            return;
        }
        this.dialog.add(SnoozeDialog, {
            name: this.props.productTemplate.display_name,
            onSave: async (hours) => {
                await this.snooze(hours);
            },
        });
    }

    getActiveSnooze() {
        const product = this.props.productTemplate;
        return this.pos.getActiveSnooze(product);
    }
}
