import { expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { localization } from "@web/core/l10n/localization";
import { parseFloat as parseLocalizedFloat } from "@web/views/fields/parsers";
import "@pos_discount/app/screens/product_screen/control_buttons/control_buttons";

definePosModels();

test("global discount startingValue uses locale decimal separator", async () => {
    const store = await setupPosEnv();
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });
    store.config.discount_pc = 8.33;

    let capturedProps;
    const buttons = {
        pos: store,
        dialog: {
            add: (_, props) => {
                capturedProps = props;
            },
        },
        env: {
            utils: {
                parseValidFloat: parseLocalizedFloat,
            },
        },
    };

    await ControlButtons.prototype.clickDiscount.call(buttons);
    expect(capturedProps.startingValue).toBe("8,33");

    let appliedDiscount;
    buttons.applyDiscount = (value) => {
        appliedDiscount = value;
    };
    capturedProps.getPayload(capturedProps.startingValue, "percent");
    expect(appliedDiscount).toBe(8.33);
});
