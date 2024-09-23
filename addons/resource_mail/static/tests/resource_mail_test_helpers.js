import { resourceModels } from "@resource/../tests/resource_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

export function defineResourceModels() {
    return defineModels({ ...mailModels, ...resourceModels });
}
