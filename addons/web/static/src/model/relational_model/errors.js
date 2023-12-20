/* @odoo-module */

import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { routeToUrl, router } from "@web/core/browser/router";
import { _t } from "@web/core/l10n/translation";

export class FetchRecordError extends Error {
    constructor(resIds, resModel) {
        if (resIds.length > 1) {
            super(
                _t(
                    "It seems the records with IDs %s cannot be found. They might have been deleted.",
                    resIds
                )
            );
        } else {
            super(
                _t(
                    "It seems the record with ID %s cannot be found. It might have been deleted.",
                    resIds
                )
            );
        }
        this.resIds = resIds;
        this.resModel = resModel;
    }
}

export function fetchRecordErrorHandler(env, error, originalError) {
    if (originalError instanceof FetchRecordError) {
        env.services.notification.add(originalError.message, { sticky: true, type: "danger" });
        const route = { ...router.current };
        const { resIds, resModel } = originalError;
        if (resIds.length === 1 && resIds[0] === route.hash.id && resModel === route.hash.model) {
            delete route.hash.id;
            delete route.hash.view_type;
            redirect(routeToUrl(route));
        }
        return true;
    }
}
const errorHandlerRegistry = registry.category("error_handlers");
errorHandlerRegistry.add("fetchRecordErrorHandler", fetchRecordErrorHandler);
