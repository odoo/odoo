import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export const TEST_CONSTANT1 = "test constant rouge";
export const TEST_CONSTANT2 = "test constant bleu";

export class BuilderOptionsContextPlugin extends Plugin {
    static id = "builderOptionsContextPlugin";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_options_context: {
            testConstant1: TEST_CONSTANT1,
            testConstant2: TEST_CONSTANT2,
        },
    };
}

registry
    .category("builder-plugins")
    .add(BuilderOptionsContextPlugin.id, BuilderOptionsContextPlugin);
