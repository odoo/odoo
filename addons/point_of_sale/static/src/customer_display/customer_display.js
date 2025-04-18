import { Component, useEffect, whenReady } from "@odoo/owl";
import { OdooLogo } from "@point_of_sale/app/components/odoo_logo/odoo_logo";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { mountComponent } from "@web/env";
import { TagsList } from "@web/core/tags_list/tags_list";
import { CustomerFacingQR } from "./customer_facing_qr";

function useSingleDialog() {
    let close = null;
    const dialog = useService("dialog");
    return {
        open(dialogClass, props) {
            // If the dialog is already open, we don't want to open a new one
            if (!close) {
                close = dialog.add(dialogClass, props, {
                    onClose: () => {
                        close = null;
                    },
                });
            }
        },
        close() {
            close?.();
        },
    };
}

export class CustomerDisplay extends Component {
    static template = "point_of_sale.CustomerDisplay";
    static components = { OdooLogo, MainComponentsContainer, TagsList };
    static props = [];

    setup() {
        this.session = session;
        this.dialog = useService("dialog");
        this.order = useService("customer_display_data");
        const singleDialog = useSingleDialog();

        useEffect(
            (qrPaymentData) => {
                if (qrPaymentData) {
                    singleDialog.open(CustomerFacingQR, qrPaymentData);
                } else {
                    singleDialog.close();
                }
            },
            () => [this.order.qrPaymentData]
        );
    }

    getInternalNotes() {
        return JSON.parse(this.line.internalNote || "[]");
    }
}

whenReady(() => mountComponent(CustomerDisplay, document.body));
