import { classAction } from "@html_builder/core/plugins/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export const card_parent_handlers =
    ".s_three_columns .row > div, .s_comparisons .row > div, .s_cards_grid .row > div, .s_cards_soft .row > div, .s_product_list .row > div, .s_newsletter_centered .row > div, .s_company_team_spotlight .row > div, .s_comparisons_horizontal .row > div, .s_company_team_grid .row > div, .s_company_team_card .row > div, .s_carousel_cards_item";

class CardWidthOptionPlugin extends Plugin {
    static id = "cardOption";
    static dependencies = ["builderActions"];
    resources = {
        builder_options: [
            withSequence(20, {
                template: "html_builder.CardWidthOption",
                selector: ".s_card",
                exclude: `div:is(${card_parent_handlers}) > .s_card`,
            }),
        ],
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
