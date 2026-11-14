import {Plugin} from "@html_editor/plugin";
import {SnippetOptions} from './multi_classes_id_options'
import {registry} from "@web/core/registry";
import {BuilderAction} from "@html_builder/core/builder_action";


class SnippetOptionsPlugin extends Plugin {
    static id = "snippetOptionsPlugin";
    static dependencies = ["history"];
    resources = {
        builder_options: [
            {
                OptionComponent: SnippetOptions,
                // Selectors
                selector: "section, .container, div, [class^='col-'], img, button, h1, h2, h3, h4, h5, h6, p, span, a, hr, input, select, textarea",
            },
        ],
        builder_actions: {
            SetClasses, SetID, SetStyles
        },
    }
}

export class SetClasses extends BuilderAction {
    static id = "setClasses";
}

export class SetID extends BuilderAction {
    static id = "setID";
}

export class SetStyles extends BuilderAction {
    static id = "setStyles";
}

registry.category("website-plugins").add(SnippetOptionsPlugin.id, SnippetOptionsPlugin);