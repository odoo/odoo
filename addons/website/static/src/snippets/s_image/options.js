/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";
import { MediaDialog } from "@web_editor/components/media_dialog/media_dialog";
import * as gridUtils from "@web_editor/js/common/grid_layout_utils";

options.registry.ImageSnippet = options.Class.extend({
    /**
     * @override
     */
    async onBuilt() {
        // When the placeholder has been dropped we directly open the media
        // dialog.
        await new Promise(resolve => {
            let isImageSaved = false;
            this.call("dialog", "add", MediaDialog, {
                onlyImages: true,
                save: imageEl => {
                    isImageSaved = true;
                    const parentEl = this.$target[0].parentNode;
                    // Replace the placeholder with the new image.
                    parentEl.insertBefore(imageEl, this.$target[0]);
                    parentEl.removeChild(this.$target[0]);
                    // Adapt the image to a grid item image if it is dropped as
                    // a grid item.
                    if (parentEl.classList.contains("o_grid_item")
                            && gridUtils._checkIfImageColumn(parentEl)) {
                        gridUtils._convertImageColumn(parentEl);
                    }
                },
            }, {
                onClose: () => {
                    if (!isImageSaved) {
                        // Revert the current step to exclude the step where the
                        // placeholder is added and then removed from the DOM
                        this.options.wysiwyg.odooEditor.historyRevertCurrentStep();
                        // If no image has been chosen, the placeholder is
                        // removed.
                        this.$target[0].remove();
                    }
                    resolve();
                }
            });
        });
    },
});

export default {
    ImageSnippet: options.registry.ImageSnippet,
};
