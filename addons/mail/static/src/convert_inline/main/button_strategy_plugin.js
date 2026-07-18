import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { isParagraphRelatedElement } from "@html_editor/utils/dom_info";
import { ElementLayout } from "../core/render_models";

export class ButtonStrategyPlugin extends Plugin {
    static id = "buttonStrategy";
    static dependencies = ["measurementSnapshot", "rules", "spacing", "style"];
    resources = {
        // TODO EGGMAIL rework sequence conflicts: default to sequence 11 to be after image_strategy_plugin
        // element_layout_analysis_processors: withSequence(11, this.analyzeButtonLayout.bind(this)),
        style_rules_processors: [[this.provideStyleRules.bind(this), ButtonStrategyPlugin.id]],
        element_layout_analysis_processors: this.addBottomUpConstraintsForButtons.bind(this),
    };

    // define style rules specifically for a elements
    // handle conflict with image_strategy_plugin => can not be an imageLink?

    provideStyleRules(rules) {
        // TODO EGGMAIL: maybe fine tune and only accept some values

        // some button may have width: 100%:
        // need to be alone in a paragraph
        // replace the paragraph + the link with width 100% by the link as a display block
        // inside a spacing table => sets the padding and the border, then put the link
        // inside? ...
        // rules.allow("width", { when: this.isBtn.bind(this) });
        // rules.allow("max-width", { when: this.isBtn.bind(this) });
        rules.allow(/^padding(-(top|right|bottom|left))?$/, {
            when: [this.isBtn.bind(this), this.validateSpacingValue.bind(this)],
        });
    }

    addBottomUpConstraintsForButtons(
        defaultEmailNodeArguments,
        { referenceNode, parentEmailNode }
    ) {
        // TODO EGGMAIL FOR MSO: rename the function and handle more than the constraints:
        // -> specify the padding dimensions in a structured format (for MSO) => maybe already done by spacing_plugin?
        // -> identify if the button has rounded corners and no siblings => if not, MSO can use a VML representation
        // -> is it worth it to implement the VML representation for the button? maybe not if everything can already be done
        // with mso-padding-alt => to test
        const { layout, analysis } = defaultEmailNodeArguments;
        if (!this.isBtn({ referenceNode })) {
            return defaultEmailNodeArguments;
        }
        const rawStyleInfo = this.getRawStyleInfo(referenceNode);
        if (rawStyleInfo.getPropertyValue("width") !== "100%") {
            return defaultEmailNodeArguments;
        }
        analysis.bottomUpConstraints.push((emailNode) => {
            const node =
                emailNode.lastReferenceNode ??
                this.config.referenceDocument.createElement(emailNode.layout.descendantTag);
            if (!this.isBlock(node)) {
                return;
            }
            if (isParagraphRelatedElement(node) && emailNode.layout instanceof ElementLayout) {
                emailNode.layout.tag = "DIV";
                // Purpose is to neutralize the margin of a paragraph related element, and apply
                // it through a spacing wrapper (as for all div).
                // TODO EGGMAIL: evaluate if we should only handle the margin here, or if all
                // propertyInfo need to be filtered again. (latter seems more appropriate, riskier)
                emailNode.layout.replaceStyleInfo(
                    this.filterStyleInfo(
                        emailNode.layout.getRef().styleInfo,
                        emailNode.layout.descendantTag
                    )
                );
            }
            // Apply display: block on the button layout if the parent is compatible
            layout.setAttributes({
                style: { display: { value: "block", priority: "important" } },
            });
        });
        return defaultEmailNodeArguments;
    }

    isBtn({ referenceNode }) {
        return referenceNode.nodeName === "A" && referenceNode.matches(".btn");
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(ButtonStrategyPlugin.id, ButtonStrategyPlugin);
