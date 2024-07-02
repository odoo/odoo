import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Counter } from "../src/counter";

/**
 * @hint components rendering is ASYNChronous and must be AWAITed
 * @hint `mountWithCleanup()` ("@web/../tests/web_test_helpers")
 */
test("counter is properly mounted", async () => {
    await mountWithCleanup(Counter);

    expect("button").toHaveCount(1);
    expect("button").toHaveText("Count:");
    expect("input").toHaveValue("0");
});

/**
 * @hint `click()` ("@odoo/hoot-dom")
 */
test("counter is incremented on clicks", async () => {
    await mountWithCleanup(Counter);

    click("button");
    await animationFrame();

    expect("input").toHaveValue("1");
});
