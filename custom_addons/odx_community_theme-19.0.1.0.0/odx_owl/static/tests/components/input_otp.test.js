/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { InputOTP } from "@odx_owl/components/input_otp/input_otp";

test("input otp aggregates typed value and reverses horizontal arrow movement in rtl", async () => {
    class Parent extends Component {
        static components = { InputOTP };
        static template = xml`<InputOTP dir="'rtl'" length="3" name="'otp'" />`;
    }

    await mountWithCleanup(Parent);

    await contains(`[data-odx-input-otp-slot="0"]`).focus();
    await contains(`[data-odx-input-otp-slot="0"]`).press("1");
    await animationFrame();

    expect(document.querySelector(`input[type="hidden"][name="otp"]`)?.value).toBe("1");
    expect(document.activeElement?.getAttribute("data-odx-input-otp-slot")).toBe("1");

    await contains(`[data-odx-input-otp-slot="1"]`).press("ArrowLeft");
    await animationFrame();

    expect(document.activeElement?.getAttribute("data-odx-input-otp-slot")).toBe("2");
});
