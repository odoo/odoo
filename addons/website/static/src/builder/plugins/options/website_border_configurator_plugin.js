import { ClassAction, StyleAction } from "@html_builder/core/core_builder_action_plugin";
import { CSS_SHORTHANDS } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class WebsiteBorderConfiguratorPlugin extends Plugin {
    static id = "websiteBorderConfigurator";

    resources = {
        builder_actions: { SetBorderRadiusClass, SetBorderRadiusStyle },
    };
}

class SetBorderRadiusClass extends ClassAction {
    static id = "setBorderRadiusClass";
    static dependencies = [...super.dependencies, "builderActions"];

    apply(context) {
        const setBorderRadiusStyleAction =
            this.dependencies.builderActions.getAction("setBorderRadiusStyle");

        setBorderRadiusStyleAction.clean({
            editingElement: context.editingElement,
            params: {
                mainParam: context.params.radiusActionParam.mainParam,
                extraClass: context.params.radiusActionParam.extraClass,
            },
        });

        super.apply(context);
    }
}

class SetBorderRadiusStyle extends StyleAction {
    static id = "setBorderRadiusStyle";
    static dependencies = [...super.dependencies, "builderActions"];

    apply(context) {
        const setBorderRadiusClassAction =
            this.dependencies.builderActions.getAction("setBorderRadiusClass");

        setBorderRadiusClassAction.clean({
            editingElement: context.editingElement,
            params: { mainParam: context.params.borderRadiusClasses },
        });

        super.apply(context);
    }

    clean(context) {
        super.clean(context);

        const { editingElement, params } = context;
        const { mainParam: borderRadius, extraClass } = params ?? {};

        const variablesToClean = CSS_SHORTHANDS[borderRadius];
        if (variablesToClean) {
            for (const variable of variablesToClean) {
                editingElement.style.removeProperty(variable);
            }
        }

        if (extraClass) {
            editingElement.classList.remove(extraClass);
        }
    }
}

registry
    .category("website-plugins")
    .add(WebsiteBorderConfiguratorPlugin.id, WebsiteBorderConfiguratorPlugin);
