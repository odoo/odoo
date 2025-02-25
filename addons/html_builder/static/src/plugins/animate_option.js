import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../core/default_builder_components";
import { useDomState, useIsActiveItem } from "../core/building_blocks/utils";
import { KeepLast } from "@web/core/utils/concurrency";

export class AnimateOption extends Component {
    static template = "html_builder.AnimateOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        getDirectionsItems: Function,
        getEffectsItems: Function,
        canHaveHoverEffect: Function,
    };

    setup() {
        this.isActiveItem = useIsActiveItem();

        const keeplast = new KeepLast();
        this.state = useDomState((editingElement) => {
            const hasAnimateClass = editingElement.classList.contains("o_animate");

            // todo: maybe add a spinner
            keeplast.add(this.props.canHaveHoverEffect(editingElement)).then((result) => {
                this.state.canHover = result;
            });

            return {
                isOptionActive: this.isOptionActive(editingElement),
                hasAnimateClass: hasAnimateClass,
                canHover: false,
                isLimitedEffect: this.limitedEffects.some((className) =>
                    editingElement.classList.contains(className)
                ),
                showIntensity: this.shouldShowIntensity(editingElement, hasAnimateClass),
                effectItems: this.props.getEffectsItems(this.isActiveItem),
                directionItems: this.props
                    .getDirectionsItems(editingElement)
                    .filter((i) => !i.check || i.check(editingElement)),
                isInDropdown: editingElement.closest(".dropdown"),
            };
        });
    }
    get limitedEffects() {
        // Animations for which the "On Scroll" and "Direction" options are not
        // available.
        return [
            "o_anim_flash",
            "o_anim_pulse",
            "o_anim_shake",
            "o_anim_tada",
            "o_anim_flip_in_x",
            "o_anim_flip_in_y",
        ];
    }

    isOptionActive(editingElement) {
        if (editingElement.matches("img")) {
            return isImageSupportedForStyle(editingElement);
        }
        return true;
    }

    shouldShowIntensity(editingElement, hasAnimateClass) {
        if (!hasAnimateClass) {
            return false;
        }
        if (!editingElement.classList.contains("o_anim_fade_in")) {
            return true;
        }

        const possibleDirections = this.props
            .getDirectionsItems()
            .map((i) => i.className)
            .filter(Boolean);
        const hasDirection = possibleDirections.some((direction) =>
            editingElement.classList.contains(direction)
        );

        return hasDirection;
    }
}

/**
 * @param {HTMLImageElement} img
 * @returns {Boolean}
 */
export function isImageSupportedForStyle(img) {
    if (!img.parentElement) {
        return false;
    }

    // See also `[data-oe-type='image'] > img` added as data-exclude of some
    // snippet options.
    const isTFieldImg = "oeType" in img.parentElement.dataset;

    // Editable root elements are technically *potentially* supported here (if
    // the edited attributes are not computed inside the related view, they
    // could technically be saved... but as we cannot tell the computed ones
    // apart from the "static" ones, we choose to not support edition at all in
    // those "root" cases).
    // See also `[data-oe-xpath]` added as data-exclude of some snippet options.
    const isEditableRootElement = "oeXpath" in img.dataset;

    return !isTFieldImg && !isEditableRootElement;
}
