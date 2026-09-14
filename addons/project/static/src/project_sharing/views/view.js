/** @odoo-module native */
import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { View } from "@web/views/view";

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
        const mode = session.project_sharing_access_mode;
        const archInfo = this.componentProps?.archInfo;
        if (!archInfo || !mode || mode === "advanced_edit") {
            return;
        }
        const restricted = { ...archInfo, recordsDraggable: false };
        if (mode === "view" && archInfo.activeActions) {
            restricted.activeActions = {
                ...archInfo.activeActions,
                create: false,
                edit: false,
                delete: false,
                duplicate: false,
            };
        }
        const componentProps = { ...this.componentProps, archInfo: restricted };
        if (mode === "view" && "readonly" in componentProps) {
            componentProps.readonly = true;
        }
        this.componentProps = componentProps;
    },
});
