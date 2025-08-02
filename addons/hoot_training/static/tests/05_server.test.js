import { expect, test } from "@odoo/hoot";
import { click, edit, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { ServerCalculator } from "../src/server_calculator";

function mockAdd(...values) {
    return values.reduce((a, b) => a + b, 0);
}

function mockMultiply(...values) {
    return values.reduce((a, b) => a * b, 1);
}

/**
 * @hint `onRpc()` ("@web/../tests/web_test_helpers")
 * @hint `expect().resolves.toBe()`
 */
test.todo("test ORM service", async () => {
    await makeMockEnv();
    const orm = getService("orm");

    await expect(orm.call("ir.calculator", "multiply", [1, 2, 3, 4])).toBe(1 * 2 * 3 * 4);
});

/**
 * @hint `onRpc()` can handle both ORM calls and generic routes
 */
test.todo("server calculator can add and multiply", async () => {
    await mountWithCleanup(ServerCalculator);

    // !FIXME: doesn't work with multiply
    patchWithCleanup(window, {
        fetch: (url, params) => {
            const args = JSON.parse(params?.body || "[]");
            let result;
            if (url.endsWith("/calculator/add")) {
                result = mockAdd(args);
            } else {
                result = mockMultiply(args);
            }
            return new Response(JSON.stringify({ result }), {
                headers: { "Content-Type": "application/json" },
            });
        },
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
