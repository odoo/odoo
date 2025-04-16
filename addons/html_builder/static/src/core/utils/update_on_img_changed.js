import { BuilderComponent } from "../building_blocks/builder_component";
import { useDomState } from "../utils";
import { LoadImgComponent } from "./load_img_component";

export class UpdateOptionOnImgChanged extends BuilderComponent {
    static template = "html_builder.UpdateOptionOnImgChanged";
    static props = { slots: { type: Object } };
    static components = { LoadImgComponent };

    setup() {
        super.setup();
        let boolean = true;
        this.state = useDomState((editingElement) => {
            const imageEls = editingElement.querySelectorAll("img");
            for (const imageEl of imageEls) {
                if (!imageEl.complete) {
                    // Rerender the slot if an image is not loaded
                    boolean = !boolean;
                    break;
                }
            }
            return {
                bool: boolean,
            };
        });
    }
}
