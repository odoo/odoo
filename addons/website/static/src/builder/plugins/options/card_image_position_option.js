import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { onceAllImagesLoaded } from "@website/utils/images";

export class CardImagePositionOption extends BaseOptionComponent {
    static template = "website.CardImagePositionOption";
    static props = {
        label: { type: String },
        level: { type: Number, optional: true },
    };
    static defaultProps = {
        level: 0,
    };

    setup() {
        super.setup();
        this.state = useDomState(async (editingElement) => {
            const imageEl = editingElement.querySelector(".o_card_img");
            if (!imageEl || "shape" in imageEl.dataset) {
                return { show: false };
            }
            await onceAllImagesLoaded(imageEl);
            const delta = this.env.editor.shared.cardImageOption.getDelta(imageEl);
            const deltaMax = Math.max(Math.abs(delta.x), Math.abs(delta.y));
            // We only show the option if the image can at least move 5px in one
            // direction
            return { show: deltaMax > 5 };
        });
    }
}
