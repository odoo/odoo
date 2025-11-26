import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { CardImageAlignmentOption } from "./card_image_alignment_option";

export class CardImageOption extends BaseOptionComponent {
    static template = "website.CardImageOption";
    static components = { CardImageAlignmentOption };

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            // Filter to exclude cover images coming from nested cards
            const coverImage = [...editingElement.querySelectorAll(".o_card_img_wrapper")].filter(
                (node) => node.closest(".s_card") === editingElement
            );
            return {
                hasCoverImage: !!coverImage.length,
            };
        });
    }
}
