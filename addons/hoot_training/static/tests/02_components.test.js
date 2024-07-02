import { expect, test } from "@odoo/hoot";
import { mount } from "@odoo/owl";

import { Counter } from "../src/counter";

/**
 * @hint components rendering is ASYNChronous and must be AWAITed
 * @hint `mountWithCleanup()` and `animationFrame` ("@web/../tests/web_test_helpers")
 * @hint input values are strings
 */
test.todo("counter is properly mounted", () => {
    mount(Counter, document.body);

    expect("button").toHaveCount(1);
    expect("button").toHaveText("Count:");
    expect("input").toHaveValue(0);
});

/**
 * @hint `click()` ("@odoo/hoot-dom")
 */
test.todo("counter is incremented on clicks", () => {
    mount(Counter, document.body);

    document.querySelector("button").click();

    expect("input").toHaveValue(1);
});
