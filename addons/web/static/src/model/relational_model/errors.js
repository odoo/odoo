import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class FetchRecordError extends Error {
    constructor(resIds) {
        super(
            _t(
                "It seems the records with IDs %s cannot be found. They might have been deleted.",
                resIds
            )
        );
        this.resIds = resIds;
    }
}
function fetchRecordErrorHandler(env, error, originalError) {
    if (originalError instanceof FetchRecordError) {
        env.services.notification.add(originalError.message, { sticky: true, type: "danger" });
        return true;
    }
}
const errorHandlerRegistry = registry.category("error_handlers");
errorHandlerRegistry.add("fetchRecordErrorHandler", fetchRecordErrorHandler);
