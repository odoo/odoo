// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { definePreset, defineTags, isHootReady } from "@odoo/hoot";
import { runTests } from "./module_set.hoot";

function beforeFocusRequired(test) {
    if (!document.hasFocus()) {
        console.warn(
            "[FOCUS REQUIRED]",
            `test "${test.name}" requires focus inside of the browser window and will probably fail without it`
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
    }
);

// Invoke tests after the interface has finished loading.
isHootReady.then(() => runTests({ fileSuffix: ".test" }));
