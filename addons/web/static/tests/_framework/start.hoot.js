// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { runTests } from "./module_set.hoot";

// Invoke tests after the module loader finished loading.
queueMicrotask(() => runTests({ fileSuffix: ".test" }));
