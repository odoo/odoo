import { parseArgs } from "node:util";

import { processOperationArg } from "./operations/operations";
import { processAddonsPathArg } from "./utils/file_path";
import { execute } from "./utils/utils";

const { values } = parseArgs({
    options: {
        "addons-path": { type: "string", default: "addons,../enterprise" },
        operation: { type: "string", default: "view_object_to_controller" },
        write: { type: "boolean", default: false },
    },
});

const directories = processAddonsPathArg(values["addons-path"]);
const operations = processOperationArg(values["operation"]);
const write = values["write"];

execute(operations, directories, write);
