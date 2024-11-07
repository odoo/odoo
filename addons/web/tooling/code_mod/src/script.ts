import { parseArgs } from "node:util";

import { put_imports_on_top } from "./operations/put_imports_on_top";
import { remove_unused_imports } from "./operations/remove_unused_imports";
import { view_object_to_controller } from "./operations/view_object_to_controller";
// import { remove_odoo_module_comment } from "./operations/remove_odoo_module_comment";
import { execute, processAddonsPath } from "./utils/utils";

const { values } = parseArgs({
    options: {
        "addons-path": { type: "string", default: "addons,../enterprise" },
        write: { type: "boolean", default: false },
    },
});

const directories = processAddonsPath(values["addons-path"]);
const operations = [
    // view_object_to_controller,
    remove_unused_imports,
    // put_imports_on_top,
];

execute(operations, directories, values["write"]);
