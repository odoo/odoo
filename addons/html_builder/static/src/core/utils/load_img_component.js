import { onWillStart } from "@odoo/owl";
import { BuilderComponent } from "../building_blocks/builder_component";

export class LoadImgComponent extends BuilderComponent {
    static template = "html_builder.LoadImgComponent";
    static props = { slots: { type: Object } };

    setup() {
        super.setup();
        onWillStart(async () => {
            const editingElements = this.env.getEditingElements();
            const promises = [];
            for (const editingEl of editingElements) {
                const imageEls = editingEl.querySelectorAll("img");
                for (const imageEl of imageEls) {
                    if (!imageEl.complete) {
                        promises.push(
                            new Promise((resolve) => {
                                imageEl.addEventListener("load", () => resolve());
                            })
                        );
                    }
                }
            }
            await Promise.all(promises);
        });
    }
}
