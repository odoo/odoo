import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";


class PurchaseOrder extends models.Model {
    _name = "purchase.order";

    name = fields.Char();

    _records = [
        { id: 1, name: "PO0001" },
    ];
}

defineModels([PurchaseOrder]);
defineMailModels();

test("disable the send reminder button while the RPC is pending", async () => {
    onRpc("purchase.order", "send_reminder_preview", () => {
        expect.step("send_reminder_preview");
        return new Promise(() => {});
    });

    await mountView({
        resModel: "purchase.order",
        resId: 1,
        type: "form",
        arch: `
            <form>
                <widget name="toaster_button"
                        title="Preview"
                        button_name="send_reminder_preview"/>
            </form>
        `,
    });

    const button = ".o_widget_toaster_button button";
    expect(button).not.toHaveAttribute("disabled");
    await contains(button).click();
    expect(button).toHaveAttribute("disabled");
    expect.verifySteps(["send_reminder_preview"]);
});
