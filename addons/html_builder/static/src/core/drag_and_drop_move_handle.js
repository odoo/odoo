import { Component, onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class DragAndDropMoveHandle extends Component {
    static template = "html_builder.DragAndDropMoveHandle";
    static props = {
        onRenderedCallback: { type: Function },
    };

    setup() {
        this.title = _t("Drag and move");

        onMounted(() => {
            this.props.onRenderedCallback();
        });
    }
}
