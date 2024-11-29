import { ResourceTask } from "./mock_server/mock_models/resource_task";
import { ResourceResource } from "./mock_server/mock_models/resource_resource";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

export const resourceModels = {
    ResourceTask,
    ResourceResource,
};

export function defineResourceModels() {
    return defineModels({ ...mailModels, ...resourceModels });
}
