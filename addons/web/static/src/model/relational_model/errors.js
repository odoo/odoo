/* @odoo-module */

import { registry } from "@web/core/registry";
import { router } from "@web/core/browser/router";

export class FetchRecordError extends Error {
    constructor(resIds, resModel) {
        super();
        this.resIds = resIds;
        this.resModel = resModel;
    }
}

export function fetchRecordErrorHandler(env, error, originalError) {
    if (originalError instanceof FetchRecordError) {
        const route = { ...router.current };
        const { resIds, resModel } = originalError;
        if (resIds.length === 1 && resIds[0] === route.id && resModel === route.model) {
            route.pushState({ id: undefined, view_type: undefined }, { reload: true });
        }
        return true;
    }
}
const errorHandlerRegistry = registry.category("error_handlers");
errorHandlerRegistry.add("fetchRecordErrorHandler", fetchRecordErrorHandler);
