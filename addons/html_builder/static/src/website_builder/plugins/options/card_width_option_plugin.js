import { classAction } from "@html_builder/core/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class CardWidthOptionPlugin extends Plugin {
    static id = "cardWidthOption";
    static dependencies = ["builderActions"];
    resources = {
        builder_actions: {
            p: this,
            get setCardWidth() {
                return this.p.getCardWidthAction();
            },
            setCardAlignment: {
                ...classAction,
                isApplied: (...args) => {
                    const {
                        editingElement: el,
                        param: { mainParam: classNames },
                    } = args[0];
                    // Align-left button is active by default
                    if (classNames === "me-auto") {
                        return !["mx-auto", "ms-auto"].some((cls) => el.classList.contains(cls));
                    }
                    return classAction.isApplied(...args);
                },
            },
        },
    };

    getCardWidthAction() {
        const styleAction = this.dependencies.builderActions.getAction("styleAction");
        return {
            ...styleAction,
            getValue: (...args) => {
                const value = styleAction.getValue(...args);
                return value.includes("%") ? value : "100%";
            },
        };
    }
}

registry.category("website-plugins").add(CardWidthOptionPlugin.id, CardWidthOptionPlugin);
