import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

class MasonryBlockTemplateOptionPlugin extends Plugin {
    static id = "mass_mailing.MasonryBlock";
    resources = {
        builder_options: [MasonryBlockTemplateOption],
        builder_actions: {
            ChangeMasonryTemplate,
        },
    };
}

class MasonryBlockTemplateOption extends BaseOptionComponent {
    static template = "mass_mailing.MasonryBlockTemplateOption";
    static selector = ".s_masonry_block";
    static groups = ["base.group_user"];
}

class ChangeMasonryTemplate extends BuilderAction {
    static id = "changeMasonryTemplate";
    apply({ editingElement, value }) {
        editingElement.dataset.templateName = value;
        const templateName = `mass_mailing.s_masonry_block_${value}`;
        const newTemplate = renderToElement(templateName);
        newTemplate.dataset.templateName = value;
        const target = editingElement.querySelector(".container");
        target.replaceChildren(newTemplate);
    }
    isApplied({ editingElement, value }) {
        return editingElement.dataset.templateName === value;
    }
}

registry
    .category("mass_mailing-plugins")
    .add(MasonryBlockTemplateOptionPlugin.id, MasonryBlockTemplateOptionPlugin);
