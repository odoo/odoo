import { parseArgs } from "node:util";

import { execute, processAddonsPath, processOperation } from "./utils/utils";

const { values } = parseArgs({
    options: {
        "addons-path": { type: "string", default: "addons,../enterprise" },
        operation: { type: "string", default: "view_object_to_controller" },
        write: { type: "boolean", default: false },
    },
});

const directories = processAddonsPath(values["addons-path"]);
const operations = processOperation(values["operation"]);

execute(operations, directories, values["write"]);
