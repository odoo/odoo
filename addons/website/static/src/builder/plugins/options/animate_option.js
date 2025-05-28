import { KeepLast } from "@web/core/utils/concurrency";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { isImageSupportedForStyle } from "@website/builder/plugins/image/replace_media_option";

export class AnimateOption extends BaseOptionComponent {
    static template = "website.AnimateOption";
    static props = {
        getDirectionsItems: Function,
        getEffectsItems: Function,
        canHaveHoverEffect: Function,
    };

    setup() {
        super.setup();
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
