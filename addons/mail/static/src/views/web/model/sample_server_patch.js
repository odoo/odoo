import { SampleServer } from "@web/model/sample_server";
import { patch } from "@web/core/utils/patch";

/**
 * If `activity_exception_decoration` is set, 'Warning' is displayed
 * instead of the last activity, and we don't want to see a bunch of
 * 'Warning's in a list.
 */
patch(SampleServer.prototype, {
    _getRandomSelectionValue(modelName, field) {
        if (field.name === "activity_exception_decoration") {
            return false;
        }
        return super._getRandomSelectionValue(...arguments);
    },
});
