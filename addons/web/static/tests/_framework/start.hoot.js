// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { definePreset, defineTags } from "@odoo/hoot";
import { runTests } from "./module_set.hoot";

definePreset("desktop", {
    icon: "fa-desktop",
    label: "Desktop",
    platform: "linux",
    size: [1366, 768],
    tags: ["-mobile"],
    touch: false,
});
definePreset("mobile", {
    icon: "fa-mobile font-bold",
    label: "Mobile",
    platform: "android",
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
        before: (test) => {
            if (!document.hasFocus()) {
                console.warn(
                    "[FOCUS REQUIRED]",
                    `test "${test.name}" requires focus inside of the browser window and will probably fail without it`
                );
            }
        },
    }
);

// Invoke tests after the module loader finished loading.
queueMicrotask(() => runTests({ fileSuffix: ".test" }));
