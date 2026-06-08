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
});
