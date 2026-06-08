import { mailModels } from "@mail/../tests/mail_test_helpers";
import { resourceModels } from "@resource/../tests/resource_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

export function defineResourceMailModels() {
    return defineModels({ ...mailModels, ...resourceModels });
}
