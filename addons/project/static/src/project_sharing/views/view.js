import { patch } from "@web/core/utils/patch";
import { router } from "@web/core/browser/router";
import { session } from "@web/session";
import { View } from "@web/views/view";

/** Hack to display the project name when we load project sharing */
patch(View.prototype, {
    setup() {
        super.setup();
        if (
            router.current.action === "project_sharing" &&
            !router.current.resId &&
            router.current.active_id === session.project_id
        ) {
            this.env.config.setDisplayName(session.project_name);
        }
    },

    async loadView(props) {
        await super.loadView(props);
        // prepare the readonly view for collaborators with view access only (nothing is editable)
        if (
            router.current.action === "project_sharing" &&
            session.portal_is_readonly &&
            this.componentProps &&
            this.componentProps.archInfo
        ) {
            const archInfo = this.componentProps.archInfo;
            if (archInfo.activeActions) {
                archInfo.activeActions.create = false;
                archInfo.activeActions.edit = false;
                archInfo.activeActions.delete = false;
                archInfo.activeActions.duplicate = false;
                archInfo.activeActions.quickCreate = false;
            }
            archInfo.recordsDraggable = false;
            if (archInfo.templateDocs && archInfo.templateDocs.menu) {
                delete archInfo.templateDocs.menu;
            }
        }
    },
});
