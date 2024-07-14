/** @odoo-module */
import { ViewButton } from "@web/views/view_button/view_button";
import { useStudioRef, studioIsVisible } from "@web_studio/client_action/view_editor/editors/utils";
import { useBus } from "@web/core/utils/hooks";

/*
 * ViewButton:
 * - Deals with invisible
 * - Click is overriden not to trigger the bound action
 */
export class ViewButtonStudio extends ViewButton {
    setup() {
        super.setup();
        useStudioRef("rootRef");

        if (this.props.studioApproval) {
            useBus(this.env.viewEditorModel.env.bus, "approval-update", () => {
                this.approval.fetchApprovals();
            });
        }
    }
    getClassName() {
        let className = super.getClassName();
        if (!studioIsVisible(this.props)) {
            className += " o_web_studio_show_invisible";
        }
        if (this.props.studioXpath) {
            className += " o-web-studio-editor--element-clickable";
        }
        return className;
    }

    onClick(ev) {
        if (this.props.tag === "a") {
            ev.preventDefault();
        }
        if (!this.props.studioXpath) {
            return;
        }
        this.env.config.onNodeClicked(this.props.studioXpath);
    }
}
ViewButtonStudio.template = "web_studio.ViewButton";
ViewButtonStudio.props = [...ViewButton.props, "studioIsVisible?", "studioXpath?"];
