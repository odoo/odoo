import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * The texts of an inline SVG cannot be edited in the page in translate mode,
 * as the browsers ignore `contenteditable` on SVG elements: their terms are
 * wrapped in a `<tspan>` (instead of a `<span>`) and translated in the
 * options of the SVG, as the translatable attributes.
 */
export const SVG_TRANSLATION_SELECTOR = "tspan[data-oe-translation-source-sha]";

/**
 * @param {SVGSVGElement} svgEl
 * @returns {SVGTSpanElement[]} the translation wrappers of the texts of the SVG
 */
export function getSvgTranslationEls(svgEl) {
    return [...svgEl.querySelectorAll(SVG_TRANSLATION_SELECTOR)];
}

export class SvgTextTranslationPlugin extends Plugin {
    static id = "svgTextTranslation";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: { TranslateSvgTextAction },
        builder_options_render_context: {
            translateSvgTextOptionSelector: `svg:has(${SVG_TRANSLATION_SELECTOR})`,
        },
    };
}

registry.category("translation-plugins").add(SvgTextTranslationPlugin.id, SvgTextTranslationPlugin);

export class TranslateSvgTextAction extends BuilderAction {
    static id = "translateSvgText";

    getValue({ editingElement, params: { mainParam: index } }) {
        return getSvgTranslationEls(editingElement)[index].textContent;
    }

    apply({ editingElement, params: { mainParam: index }, value }) {
        const translationEl = getSvgTranslationEls(editingElement)[index];
        translationEl.textContent = value;
        translationEl.classList.add("o_dirty");
        translationEl.dataset.oeTranslationState = "translated";
    }
}
