import { Plugin } from "@html_editor/plugin";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultOptionComponents } from "../components/defaultComponents";
import { withSequence } from "@html_editor/utils/resource";

class AnimateOptionPlugin extends Plugin {
    static id = "AnimateOption";
    resources = {
        builder_options: [
            withSequence(20, {
                OptionComponent: AnimateOption,
                selector: ".o_animable, section .row > div, img, .fa, .btn, .o_animated_text",
                exclude:
                    "[data-oe-xpath], .o_not-animable, .s_col_no_resize.row > div, .s_col_no_resize",
                // todo: to implement
                // textSelector: ".o_animated_text",
            }),
        ],
        builder_actions: this.getActions(),
    };
    getActions() {
        return {
            setAnimationMode: {
                isActive: () => true,
                apply: () => {
                    console.warn("todo");
                },
            },
        };
    }
}
registry.category("website-plugins").add(AnimateOptionPlugin.id, AnimateOptionPlugin);

class AnimateOption extends Component {
    static template = "html_builder.AnimateOption";
    static components = { ...defaultOptionComponents };
    static props = {};
}
