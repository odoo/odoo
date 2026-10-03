import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { EffectsButton } from "./effects_panel";

/**
 * @typedef {Object} EffectsPanelSection
 * @property {string} id
 * @property {string} title
 * @property {Function} Component rendered when the section is open
 * @property {Object} props
 * @property {(selection) => boolean} [isAvailable]
 * @property {() => boolean} [isDisabled]
 * @property {() => boolean} isActive whether the selection has this effect
 * @property {() => string} getSummary the effect of the selection, shown on
 * the closed section
 * @property {() => void} [prepare] adapts the selection before the panel
 * opens (e.g. to cover a whole highlight): focusing the page afterwards would
 * close the panel
 *
 * @typedef {EffectsPanelSection[]} effects_panel_sections
 */

/**
 * One toolbar button for the text effects (shadow and outline, highlight,
 * animation...): it opens one panel with a section for each effect that a
 * plugin registers in `effects_panel_sections`.
 */
export class EffectsPanelPlugin extends Plugin {
    static id = "effectsPanel";
    static dependencies = ["selection"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        // With the other formatting of the text: after its colors, before
        // "More formatting" (sequence 30).
        toolbar_items: [
            withSequence(20, {
                id: "effects",
                groupId: "decoration",
                description: _t("Text effects"),
                Component: EffectsButton,
                props: this.getButtonProps(),
                isAvailable: (selection) => this.getAvailableSections(selection).length > 0,
            }),
            withSequence(20, {
                // When the caret is in text with an effect, the compact bar
                // opens (see the highlight and animate plugins): it shows the
                // button there too.
                id: "effects_compact",
                groupId: "decoration",
                namespaces: ["compact"],
                description: _t("Text effects"),
                Component: EffectsButton,
                props: this.getButtonProps(),
                isAvailable: (selection) =>
                    this.getAvailableSections(selection).some((section) => section.isActive()),
            }),
        ],
    };

    getButtonProps() {
        return {
            // Not in a plain editor, where the summaries refresh less often.
            config: this.config.getAnimateTextConfig?.(),
            getSections: () =>
                this.getAvailableSections(
                    this.dependencies.selection.getSelectionData().editableSelection
                ),
        };
    }

    /**
     * @returns {EffectsPanelSection[]}
     */
    getAvailableSections(selection) {
        return this.getResource("effects_panel_sections").filter(
            (section) => !section.isAvailable || section.isAvailable(selection)
        );
    }
}
