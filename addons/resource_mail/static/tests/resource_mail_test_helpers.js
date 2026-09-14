import { mailModels } from "@mail/../tests/mail_test_helpers";
import { resourceModels } from "@resource/../tests/resource_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

import { ResourceTask } from "./mock_server/mock_models/resource_task.js";

export const resourceMailModels = {
    ...resourceModels,
    ResourceTask,
};

export function defineResourceMailModels() {
    return defineModels({ ...mailModels, ...resourceMailModels });
}
