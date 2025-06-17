import { registry } from "@web/core/registry";

export const hrActionHelperService = {
    dependencies: ["orm"],
    async: ["showActionHelper"],
    start(env, { orm }) {
        let showActionHelper = null;
        return {
            async showActionHelper(reload = false) {
                if (showActionHelper == null || reload) {
                    showActionHelper = await orm.call("hr.employee", "show_action_helper");
                }
                return showActionHelper;
            },
        };
    },
};

registry.category("services").add("hr_action_helper", hrActionHelperService);
