import { SUGGESTION_DELIMITERS } from "@mail/core/common/suggestion_hook";
import { SuggestionService } from "@mail/core/common/suggestion_service";

import { patch } from "@web/core/utils/patch";

/** @type {SuggestionService} */
const suggestionServicePatch = {
    getSupportedDelimiters(thread, owner) {
        if (owner?.portalChatterPlugin?.inFrontendPortalChatter()) {
            return [
                [SUGGESTION_DELIMITERS.CANNED_RESPONSE],
                [SUGGESTION_DELIMITERS.EMOJI, undefined, 2],
            ];
        }
        return super.getSupportedDelimiters(...arguments);
    },
};
patch(SuggestionService.prototype, suggestionServicePatch);
