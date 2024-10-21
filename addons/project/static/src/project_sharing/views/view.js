import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { View } from "@web/views/view";

/** Hack to display the project name when we load project sharing */
patch(View.prototype, {
    setup() {
        super.setup();
        const params = this.props.context?.params;
        if (
            params?.action === "project_sharing" &&
            !("resId" in params) &&
            params.active_id === session.project_id
        ) {
            this.env.config.setDisplayName(session.project_name);
        }
    },
});
