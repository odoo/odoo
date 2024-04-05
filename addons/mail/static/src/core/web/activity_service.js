import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class ActivityService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.orm = services.orm;
    }

    async schedule(resModel, resIds, defaultActivityTypeId = undefined) {
        const context = {
            active_model: resModel,
            active_ids: resIds,
            active_id: resIds[0],
            ...(defaultActivityTypeId !== undefined
                ? {
                      default_activity_type_id: defaultActivityTypeId,
                  }
                : {}),
        };
        return new Promise((resolve) =>
            this.env.services.action.doAction(
                {
                    type: "ir.actions.act_window",
                    name:
                        resIds && resIds.length > 1
                            ? _t("Schedule Activity On Selected Records")
                            : _t("Schedule Activity"),
                    res_model: "mail.activity.schedule",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    context,
                },
                { onClose: resolve }
            )
        );
    }
}

export const activityService = {
    dependencies: ["mail.store", "orm"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new ActivityService(env, services);
    },
};

registry.category("services").add("mail.activity", activityService);
