import { parseArgs } from "node:util";

import { view_object_to_controller } from "./operations/view_object_to_controller";
import { execute, processAddonsPath } from "./utils/utils";

const { values } = parseArgs({
    options: {
        "addons-path": { type: "string", default: "addons,../enterprise" },
        write: { type: "boolean", default: false },
    },
});

const directories = processAddonsPath(values["addons-path"]);
const operations = [view_object_to_controller];

execute(operations, directories, values["write"]);
