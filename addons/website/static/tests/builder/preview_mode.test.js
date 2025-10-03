import { Plugin } from "@html_editor/plugin";
import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { uniqueId } from "@web/core/utils/functions";
import { addOption, addPlugin, defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { BuilderAction } from "@html_builder/core/builder_action";

defineWebsiteModels();

test("do not update builder if in preview mode", async () => {
    const pluginId = uniqueId("test-action-plugin");
    class P extends Plugin {
        static id = pluginId;
        static dependencies = ["history"];
        resources = {
            builder_actions: {
                CustomAction,
            },
        };
    }
    addPlugin(P);
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton id="'id1'" action="'customAction'">b1</BuilderButton>
        <BuilderButton classAction="'b2_class'" t-if="this.isActiveItem('id1')">b2</BuilderButton>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains("[data-action-id='customAction']").hover();
    expect("[data-class-action='b2_class']").not.toHaveCount();
    expect(".o-snippets-top-actions .fa-undo").not.toBeEnabled();
});

class CustomAction extends BuilderAction {
    static id = "customAction";
    static dependencies = ["history"];
    apply({ editingElement }) {
        editingElement.classList.add("applied");
        this.dependencies.history.addStep();
    }
    isApplied({ editingElement }) {
        return editingElement.classList.contains("applied");
    }
}
