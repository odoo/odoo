import { CustomizeWebsiteVariableAction } from "@website/builder/plugins/customize_website_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class SetFormMarkAction extends CustomizeWebsiteVariableAction {
    static id = "setFormMark";

    apply(context) {
        return super.apply({ ...context, value: `'${context.value}'` });
    }
}

export class FormMarkOptionPlugin extends Plugin {
    static id = "formMarkOption";
    resources = {
        builder_actions: { SetFormMarkAction },
    };
}

registry.category("website-plugins").add(FormMarkOptionPlugin.id, FormMarkOptionPlugin);
