import { describe, expect, test } from "@odoo/hoot";

// `timapi_loader.js` runs as a plain script (`@odoo-module ignore`) and installs
// `window.Module.locateFile` at script-load time. By the time these tests run
// it has already executed, so we assert against its observable side effects.
test("installs Module.locateFile as a function", () => {
    expect(typeof window.Module?.locateFile).toBe("function");
});

test("rewrites every .wasm request to the pos_six static URL", () => {
    const expected = "/pos_six/static/lib/six_timapi/timapi.wasm";

    // Whatever `scriptDirectory` Emscripten passes in (the bundled asset URL,
    // empty string, or undefined), the wasm must come from the module path.
    expect(window.Module.locateFile("timapi.wasm", "/web/assets/debug/")).toBe(expected);
    expect(window.Module.locateFile("timapi.wasm", "")).toBe(expected);
    expect(window.Module.locateFile("timapi.wasm")).toBe(expected);
    expect(window.Module.locateFile("anything.wasm", "/somewhere/")).not.toBe(expected);
});

test("passes non-wasm paths through, prefixed with scriptDirectory", () => {
    expect(window.Module.locateFile("helper.js", "/lib/")).toBe("/lib/helper.js");
    expect(window.Module.locateFile("data.json", "/web/assets/")).toBe("/web/assets/data.json");
});

test("non-wasm paths with no scriptDirectory fall back to a bare relative path", () => {
    expect(window.Module.locateFile("helper.js")).toBe("helper.js");
    expect(window.Module.locateFile("data.json", "")).toBe("data.json");
});
