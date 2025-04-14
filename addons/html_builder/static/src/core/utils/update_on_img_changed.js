import { BuilderComponent } from "../building_blocks/builder_component";
import { useDomState } from "../utils";

export class UpdateOptionOnImgChanged extends BuilderComponent {
    static template = "html_builder.UpdateOptionOnImgChanged";
    static props = {};

    setup() {
        super.setup();
        let boolean = true;
        this.state = useDomState((editingElement) => {
            const imageEl = editingElement.querySelector("img");
            if (imageEl && !imageEl.complete) {
                // Rerender the slot if the image is not loaded
                boolean = !boolean;
            }
            return {
                bool: boolean,
            };
        });
    }
}
