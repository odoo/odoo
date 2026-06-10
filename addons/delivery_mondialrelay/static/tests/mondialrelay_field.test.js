import { expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, fields, models, mountView, patchWithCleanup } from "@web/../tests/web_test_helpers";

class ChooseDeliveryCarrier extends models.Model {
    _name = "choose.delivery.carrier";
    name = fields.Char();
    shipping_zip = fields.Char();
    mondialrelay_last_selected = fields.Char();
    is_mondialrelay = fields.Boolean();

    _records = [
        { id: 1, name: "Mondial Relay", shipping_zip: "1367", is_mondialrelay: true },
    ];
}

defineMailModels();
defineModels({
    ChooseDeliveryCarrier,
});

test("Mondial Relay field opens the widget", async () => {
    const originalAppendChild = document.head.appendChild;
    patchWithCleanup(document.head, {
        appendChild: (node) => {
            if (!node.getAttribute("src").endsWith("jquery.plugin.mondialrelay.parcelshoppicker.min.js")) {
                return originalAppendChild.call(document.head, node);
            }
            expect(node).toBeInstanceOf(HTMLScriptElement);
            expect(node).toHaveAttribute("type", "text/javascript");
            node.removeAttribute("src");
            node.textContent = `
                $.fn.MR_ParcelShopPicker = function(params) {
                    this.text("MR_ParcelShopPicker called with zip code: " + params.PostCode);
                    return this;
                };
            `;
            originalAppendChild.call(document.head, node);
            manuallyDispatchProgrammaticEvent(node, "load");
            return node;
        },
    });
    await mountView({
        type: "form",
        resId: 1,
        resModel: "choose.delivery.carrier",
        arch: `
            <form>
                <field name="name"/>
                <field name="shipping_zip" invisible="1"/>
                <field name="is_mondialrelay" invisible="1"/>
                <field name="mondialrelay_last_selected" widget="mondialrelay_relay"/>
            </form>`,
    });
    expect(".o_field_mondialrelay_relay > div").toHaveText("MR_ParcelShopPicker called with zip code: 1367");
});
