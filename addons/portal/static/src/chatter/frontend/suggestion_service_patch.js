import { SuggestionService } from "@mail/core/common/suggestion_service";

import { patch } from "@web/core/utils/patch";

/** @type {SuggestionService} */
const suggestionServicePatch = {
    getSupportedDelimiters(thread, env) {
        if (env?.inFrontendPortalChatter) {
            return [["::"], [":", undefined, 2]];
        }
        return super.getSupportedDelimiters(...arguments);
    },
};
patch(SuggestionService.prototype, suggestionServicePatch);
