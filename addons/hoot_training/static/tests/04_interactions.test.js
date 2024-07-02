import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Counter } from "../src/counter";

/**
 * @hint `click()` ("@odoo/hoot-dom")
 */
test.todo("counter is incremented on clicks", async () => {
    await mountWithCleanup(Counter);

    expect("input").toHaveValue("0");

    document.querySelector("button").click();
    await animationFrame();

    expect("input").toHaveValue("1");
});

/**
 * @hint `press()` ("@odoo/hoot-dom")
 */
test.todo("counter is incremented on 'Enter' presses", async () => {
    await mountWithCleanup(Counter);

    expect("input").toHaveValue("0");

    document.querySelector("button").dispatchEvent(new KeyboardEvent("keydown", { key: "Tab" }));
    document.querySelector("button").dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    await animationFrame();

    expect("input").toHaveValue("1");
});

/**
 * @hint check the name of the test
 * @hint `click()` and `edit()` ("@odoo/hoot-dom")
 * @hint `expect().toHaveValue()`
 */
test.todo("counter is incremented after being edited", async () => {
    await mountWithCleanup(Counter);

    expect("input").toHaveValue("0");

    document.querySelector("input").value = "17";
    document.querySelector("input").dispatchEvent(new InputEvent("input"));
    document.querySelector("input").dispatchEvent(new Event("change"));
    await animationFrame();

    expect("input").toHaveValue("17");

    document.querySelector("button").click();
    await animationFrame();

    expect("input").toHaveValue("18");
});
