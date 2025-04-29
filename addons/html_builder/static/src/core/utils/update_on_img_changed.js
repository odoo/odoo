import { Component, onWillStart, xml } from "@odoo/owl";
import { useDomState } from "../utils";

class LoadImgComponent extends Component {
    static template = xml`
        <t t-slot="default"/>
    `;
    static props = { slots: { type: Object } };

    setup() {
        onWillStart(async () => {
            const editingElements = this.env.getEditingElements();
            const promises = [];
            for (const editingEl of editingElements) {
                const imageEls = editingEl.matches("img")
                    ? [editingEl]
                    : editingEl.querySelectorAll("img");
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

/**
 * In Chrome, when replacing an image on the DOM, some image properties are not
 * available even if the image has been loaded beforehand. This is a problem if
 * an option is using one of those property at each DOM change (useDomState).
 * To solve the problem, this component reloads the option (and waits for the
 * images to be loaded) each time an image has been modified inside its editing
 * element.
 */
export class UpdateOptionOnImgChanged extends Component {
    // TODO: this is a hack until <t t-key="state.count" t-slot="default"/> is
    // fixed in OWL.
    static template = xml`
        <LoadImgComponent t-if="state.bool"><t t-slot="default"/></LoadImgComponent>
        <LoadImgComponent t-else=""><t t-slot="default"/></LoadImgComponent>
    `;
    static props = { slots: { type: Object } };
    static components = { LoadImgComponent };

    setup() {
        let boolean = true;
        this.state = useDomState((editingElement) => {
            const imageEls = editingElement.matches("img")
                ? [editingElement]
                : editingElement.querySelectorAll("img");
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
