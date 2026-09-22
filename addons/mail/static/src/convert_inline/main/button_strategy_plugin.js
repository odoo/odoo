import { registry } from "@web/core/registry";
import { Plugin } from "@mail/convert_inline/plugin";
import { isParagraphRelatedElement } from "@html_editor/utils/dom_info";
import { ElementLayout } from "@mail/convert_inline/core/render_models";

export class ButtonStrategyPlugin extends Plugin {
    static id = "buttonStrategy";
    static dependencies = ["measurementSnapshot", "rules", "spacing", "style"];
    resources = {
        style_rules_processors: this.provideStyleRules.bind(this),
        element_layout_analysis_processors: this.addBottomUpConstraintsForButtons.bind(this),
    };

    provideStyleRules(rules) {
        rules.allow(/^padding(-(top|right|bottom|left))?$/, {
            when: [this.isBtn.bind(this), this.validateSpacingValue.bind(this)],
        });
    }

    addBottomUpConstraintsForButtons(defaultEmailNodeArguments, { referenceNode }) {
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
                // Replace the StyleInfo to neutralize the margin of a paragraph related element,
                // and apply it through a spacing wrapper (as for all div).
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
