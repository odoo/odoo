/* @odoo-module */

import { registry } from "@web/core/registry";
import { FetchRecordError } from "./utils";
import { redirect } from "@web/core/utils/urls";
import { routeToUrl } from "@web/core/browser/router_service";

export function fetchRecordErrorHandler(env, error, originalError) {
    if (originalError instanceof FetchRecordError) {
        env.services.notification.add(originalError.message, { sticky: true, type: "danger" });
        const route = { ...env.services.router.current };
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
