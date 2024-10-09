import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

export class DragAndDropPlugin extends Plugin {
    static id = "dragAndDrop";
    resources = {
        has_overlay_options: this.isDraggable.bind(this),
        get_overlay_buttons: withSequence(1, this.getActiveOverlayButtons.bind(this)),
    };

    setup() {
        this.overlayTarget = null;
    }

    isDraggable(el) {
        const dropzoneSelectors = [];
        this.getResource("dropzone_selector").forEach((selectors) =>
            dropzoneSelectors.push(selectors)
        );
        const isDraggable = dropzoneSelectors
            .flat()
            .find(({ selector, exclude = false }) => el.matches(selector) && !el.matches(exclude));
        return !!isDraggable;
    }

    getActiveOverlayButtons(target) {
        if (!this.isDraggable(target)) {
            this.overlayTarget = null;
            return [];
        }

        const buttons = [];
        this.overlayTarget = target;
        buttons.push({
            class: "o_move_handle fa fa-arrows",
            title: _t("Drag and move"),
            handler: () => {},
        });
        return buttons;
    }
}
