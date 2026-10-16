import { expect, mockTouch, press, queryOne, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Dialog } from "@web/core/dialog/dialog";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";

definePosModels();

test("POS dialog body buttons use inset shadows without changing tab order", async () => {
    mockTouch(false);
    await setupPosEnv();
    class Parent extends Component {
        static components = { Dialog };
        static template = xml`
            <div class="pos">
                <Dialog>
                    <input class="keyboard-start"/>
                    <button class="body-action btn btn-secondary">Action</button>
                    <t t-set-slot="footer">
                        <button class="footer-action btn btn-primary">Confirm</button>
                    </t>
                </Dialog>
            </div>
        `;
    }
    await mountWithCleanup(Parent);
    expect(".keyboard-start").toBeFocused();

    // Check the configured shadows before focusing: simulated Tab does not
    // change the browser's :focus-visible input modality.
    expect(
        getComputedStyle(queryOne(".body-action")).getPropertyValue("--btn-focus-box-shadow")
    ).toInclude("inset");

    const footerShadow = getComputedStyle(queryOne(".footer-action")).getPropertyValue(
        "--btn-focus-box-shadow"
    );
    expect(footerShadow).not.toBe("none");
    expect(footerShadow).not.toInclude("inset");

    await press("Tab");
    expect(".body-action").toBeFocused();
    await press("Tab");
    expect(".footer-action").toBeFocused();
});
