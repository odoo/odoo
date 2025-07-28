import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { isImageSupportedForStyle } from "@html_builder/plugins/image/replace_media_option";

export class AnimateOption extends BaseOptionComponent {
    static template = "website.AnimateOption";
    static dependencies = ["animateOption"];
    static selector = ".o_animable, section .row > div, img, .fa, .btn";
    static exclude =
        "[data-oe-xpath], .o_not-animable, .s_col_no_resize.row > div, .s_col_no_resize";
    static props = {
        requireAnimation: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = { requireAnimation: false };

    setup() {
        super.setup();
        this.state = useDomState(async (editingElement) => {
            const hasAnimateClass = editingElement.classList.contains("o_animate");
            this.getDirectionsItems = this.dependencies.animateOption.getDirectionsItems;
            const { getEffectsItems } = this.dependencies.animateOption;

            return {
                isOptionActive: this.isOptionActive(editingElement),
                hasAnimateClass: hasAnimateClass,
                canHover: await this.canHaveHoverEffect(editingElement),
                isLimitedEffect: this.limitedEffects.some((className) =>
                    editingElement.classList.contains(className)
                ),
                showIntensity: this.shouldShowIntensity(editingElement, hasAnimateClass),
                effectItems: getEffectsItems(this.isActiveItem),
                directionItems: this.getDirectionsItems(editingElement).filter(
                    (i) => !i.check || i.check(editingElement)
                ),
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

        const possibleDirections = this.getDirectionsItems()
            .map((i) => i.className)
            .filter(Boolean);
        const hasDirection = possibleDirections.some((direction) =>
            editingElement.classList.contains(direction)
        );

        return hasDirection;
    }
    async canHaveHoverEffect(el) {
        const proms = this.getResource("hover_effect_allowed_predicates").map((p) => p(el));
        const settledProms = await Promise.all(proms);
        return settledProms.length && settledProms.every(Boolean);
    }
}
