import { expect, test } from "@odoo/hoot";
import { click, edit, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { getService, makeMockEnv, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

import { ServerCalculator } from "../src/server_calculator";

function mockAdd(...values) {
    return values.reduce((a, b) => a + b, 0);
}

function mockMultiply(...values) {
    return values.reduce((a, b) => a * b, 1);
}

/**
 * @hint `onRpc()` and `getService()` ("@web/../tests/web_test_helpers")
 * @hint `expect().resolves.toBe()`
 */
test("test ORM service", async () => {
    await makeMockEnv();
    const orm = getService("orm");

    onRpc("multiply", ({ args }) => mockMultiply(...args));

    await expect(orm.call("ir.calculator", "multiply", [1, 2, 3, 4])).resolves.toBe(1 * 2 * 3 * 4);
});

/**
 * @hint `onRpc()` can handle both ORM calls and generic routes
 */
test("server calculator can add and multiply", async () => {
    await mountWithCleanup(ServerCalculator);

    onRpc("multiply", ({ args }) => mockMultiply(...args));
    onRpc("/calculator/add", async (request) => {
        const args = await request.json();
        return mockAdd(...args);
    });

    await click("input:first");
    await edit(10);

    await click("input:last");
    await edit(5);

    await click("button:contains(+)");
    await animationFrame();

    expect(queryAllTexts(".results li")).toEqual(["15"]);

    await click("button:contains(*)");
    await animationFrame();

    expect(queryAllTexts(".results li")).toEqual(["15", "50"]);
});
