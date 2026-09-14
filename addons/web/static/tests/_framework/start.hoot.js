// @ts-check

import {
    __debug__,
    after,
    definePreset,
    defineTags,
    describe,
    isHootReady,
    start,
    test,
} from "@odoo/hoot";
import { bindCleanupHook } from "@web/../tests/helpers/cleanup";

import { patchBrowserLocation, patchBrowserStorage } from "./mock_browser.hoot.js";
import { isolateLocalizationCache } from "./mock_localization_cache.hoot.js";
import { setupTestEnvironment } from "./module_set.hoot.js";

/**
 * @param {string} value
 * @returns {string}
 */
bindCleanupHook(after);

function _hashJobId(value) {
    let hash = 0;
    for (let i = 0; i < value.length; i++) {
        hash = (hash << 5) - hash + value.charCodeAt(i);
        hash |= 0;
    }
    return (hash + 16 ** 8).toString(16).slice(-8);
}

const REQUESTED_IDS = new Set(
    new URLSearchParams(globalThis.location?.search ?? "")
        .getAll("id")
        .filter((id) => !id.startsWith("-")),
);

/** @param {any} test */
function beforeFocusRequired(test) {
    if (!document.hasFocus()) {
        console.warn(
            "[FOCUS REQUIRED]",
            `test "${test.name}" requires focus inside of the browser window and will probably fail without it`,
        );
    }
}

definePreset("desktop", {
    icon: "fa-desktop",
    label: "Desktop",
    size: [1366, 768],
    tags: ["-mobile"],
    touch: false,
});
definePreset("mobile", {
    icon: "fa-mobile font-bold",
    label: "Mobile",
    size: [375, 667],
    tags: ["-desktop"],
    touch: true,
});
defineTags(
    {
        name: "desktop",
        exclude: ["headless", "mobile"],
    },
    {
        name: "mobile",
        exclude: ["desktop", "headless"],
    },
    {
        name: "headless",
        exclude: ["desktop", "mobile"],
    },
    {
        name: "focus required",
        before: beforeFocusRequired,
    },
);

setupTestEnvironment();

patchBrowserLocation();
patchBrowserStorage();
isolateLocalizationCache();

odoo.loader._reloadPage = () => {};

const _runner = /** @type {any} */ (__debug__);

/**
 * @param {string} specifier
 * @returns {string}
 */
function _suiteNameFromSpecifier(specifier) {
    const m = specifier.match(/^(@[^/]+)\/\.\.\/tests\/(.*?)(?:\.test)?$/);
    return m ? `${m[1]}/${m[2]}` : specifier;
}

/**
 * @param {string[]} testSpecifiers
 * @returns {string[]}
 */
function _selectTestSpecifiers(testSpecifiers) {
    if (!REQUESTED_IDS.size) {
        return testSpecifiers;
    }
    const unresolvedIds = new Set(REQUESTED_IDS);
    const isSelected = (/** @type {any} */ specifier) => {
        if (!specifier.endsWith(".test")) {
            return true;
        }
        const parts = _suiteNameFromSpecifier(specifier).split("/");
        let selected = false;
        for (let i = 0; i < parts.length; i++) {
            const id = _hashJobId(parts.slice(0, i + 1).join("/"));
            if (REQUESTED_IDS.has(id)) {
                unresolvedIds.delete(id);
                selected = true;
            }
        }
        return selected;
    };
    const selected = testSpecifiers.filter(isSelected);
    // Individual test IDs become known only after import. A recognized suite ID
    // must not prevent another requested test's module from being imported.
    return unresolvedIds.size ? testSpecifiers : selected;
}

/** @param {...any} parts */
function _bootLog(...parts) {
    console.debug("[HOOT][boot]", ...parts);
}

/** @param {...any} parts */
function _bootWarn(...parts) {
    console.warn("[HOOT][boot]", ...parts);
}

/** @param {string[]} specifiers */
function _preloadTestModules(specifiers) {
    const importMap = document.querySelector('script[type="importmap"]');
    if (!importMap?.textContent) {
        return;
    }
    let imports;
    try {
        imports = JSON.parse(importMap.textContent).imports;
    } catch {
        return;
    }
    if (!imports) {
        return;
    }
    const fragment = document.createDocumentFragment();
    for (const specifier of specifiers) {
        const href = imports[specifier];
        if (!href) {
            continue;
        }
        const link = document.createElement("link");
        link.rel = "modulepreload";
        link.href = href;
        fragment.append(link);
    }
    document.head.append(fragment);
}

/** @param {string} specifier */
async function _importInFileSuite(specifier) {
    const suiteName = _suiteNameFromSpecifier(specifier);
    /** @type {any} */
    let fileSuite;
    describe(suiteName, () => {
        fileSuite = _runner.suiteStack.at(-1);
    });
    if (!fileSuite) {
        return import(specifier);
    }
    _runner.suiteStack.push(fileSuite);
    try {
        return await import(specifier);
    } catch (reason) {
        // a file that does not import registers no test, and a run that only
        // counts registered tests would report it green: it fails as one
        test("module imports", () => {
            throw reason;
        });
        throw reason;
    } finally {
        _runner.suiteStack.pop();
    }
}

/** @param {string[]} allTestSpecifiers */
export async function loadAndStart(allTestSpecifiers) {
    _bootLog(`called with ${allTestSpecifiers.length} specifier(s)`);
    if (!allTestSpecifiers.length) {
        _bootWarn(
            "no test specifiers were passed — this page can only report zero " +
                "tests. The bundle's generated entry supplies them; check that " +
                "it carries both `start.hoot` and the test files.",
        );
    }
    await isHootReady;
    _bootLog("hoot ready");
    const testSpecifiers = _selectTestSpecifiers(allTestSpecifiers);
    if (testSpecifiers.length !== allTestSpecifiers.length) {
        _bootLog(
            `id filter selected ${testSpecifiers.length}/${allTestSpecifiers.length}`,
        );
    }
    if (allTestSpecifiers.length && !testSpecifiers.length) {
        _bootWarn("the id filter selected nothing — no test will run");
    }
    _preloadTestModules(testSpecifiers);
    /** @type {Array<{status: "fulfilled" | "rejected", value?: any, reason?: any}>} */
    const results = [];
    for (const spec of testSpecifiers) {
        try {
            const value = await _importInFileSuite(spec);
            results.push({ status: "fulfilled", value });
        } catch (e) {
            results.push({ status: "rejected", reason: e });
        }
    }
    const loaded = results.filter((r) => r.status === "fulfilled").length;
    _bootLog(`imported ${loaded}/${testSpecifiers.length} test module(s)`);
    if (testSpecifiers.length && !loaded) {
        _bootWarn(
            "every test module failed to import — the runner will start with " +
                "nothing registered; see the [HOOT][import-fail] lines above",
        );
    }
    const failed = results
        .map((r, i) => ({ result: r, specifier: testSpecifiers[i] }))
        .filter(({ result }) => result.status === "rejected");
    if (failed.length) {
        const grouped = new Map();
        for (const { result, specifier } of failed) {
            const reason = result.reason;
            const key = reason?.message || String(reason);
            const bucket = grouped.get(key);
            if (bucket) {
                bucket.specifiers.push(specifier);
            } else {
                let typeName;
                try {
                    typeName =
                        reason?.constructor?.name ||
                        (reason === null ? "null" : typeof reason);
                } catch {
                    typeName = "(thrown-during-introspection)";
                }
                const stack = reason?.stack || "";
                const causes = [];
                let cur = reason?.cause;
                let depth = 0;
                while (cur && depth < 5) {
                    causes.push({
                        type: cur?.constructor?.name || typeof cur,
                        message: cur?.message || String(cur),
                        stack: cur?.stack || "",
                    });
                    cur = cur?.cause;
                    depth++;
                }
                grouped.set(key, {
                    specifiers: [specifier],
                    typeName,
                    stack,
                    causes,
                });
            }
        }
        console.warn(
            `[HOOT] ${failed.length}/${testSpecifiers.length} test modules failed to import; ${grouped.size} unique error(s)`,
        );
        for (const [message, { specifiers, typeName, stack, causes }] of grouped) {
            console.warn(
                `[HOOT][import-fail][x${specifiers.length}] [${typeName}] ${message}`,
            );
            if (stack) {
                const frames = String(stack).split("\n").slice(0, 8);
                for (const f of frames) {
                    if (f.trim()) {
                        console.warn(`[HOOT][import-fail]   @ ${f.trim()}`);
                    }
                }
            } else {
                console.warn(`[HOOT][import-fail]   stack: <none>`);
            }
            for (let i = 0; i < Math.min(causes.length, 3); i++) {
                const c = causes[i];
                console.warn(
                    `[HOOT][import-fail]   cause[${i}]: [${c.type}] ${c.message}`,
                );
                if (c.stack) {
                    const causeFrames = String(c.stack).split("\n").slice(0, 6);
                    for (const f of causeFrames) {
                        if (f.trim()) {
                            console.warn(
                                `[HOOT][import-fail]   cause[${i}] @ ${f.trim()}`,
                            );
                        }
                    }
                }
            }
            for (const spec of specifiers.slice(0, 5)) {
                console.warn(`[HOOT][import-fail]   - ${spec}`);
            }
            if (specifiers.length > 5) {
                console.warn(
                    `[HOOT][import-fail]   ... +${specifiers.length - 5} more`,
                );
            }
        }
    }
    _bootLog("starting runner");
    start();
}
