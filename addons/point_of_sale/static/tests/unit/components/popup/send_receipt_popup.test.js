import { test, expect } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { getFilledOrder, setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { SendReceiptPopup } from "@point_of_sale/app/components/popups/send_receipt_popup/send_receipt_popup";

definePosModels();

test("phone and email are valid and action buttons are enabled", async () => {
    const store = await setupAndMountPosApp();
    patchWithCleanup(SendReceiptPopup.prototype, {
        showPhoneInput() {
            return true;
        },
        get sendList() {
            const list = super.sendList;
            list.find((item) => item.model === "phone").buttons.push({
                icon: "fa-comment fa-lg",
                disabled: () => !this.isValidPhone,
            });
            return list;
        },
    });
    const order = await getFilledOrder(store);
    const partner = store.models["res.partner"].get(4);
    order.partner_id = partner;

    await mountWithCleanup(SendReceiptPopup, { props: { order } });

    expect(".send-receipt-email-input").toHaveCount(1);
    expect(".send-receipt-phone-input").toHaveCount(1);

    expect(".send-receipt-email-input").not.toHaveAttribute("disabled");
    expect(".send-receipt-phone-input").not.toHaveAttribute("disabled");

    expect(".send-receipt-email-input").toHaveValue(partner.email);
    expect(".send-receipt-phone-input").toHaveValue(partner.phone_sanitized);
});
