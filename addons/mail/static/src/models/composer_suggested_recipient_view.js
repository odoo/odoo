/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "ComposerSuggestedRecipientView",
    fields: {
        composerSuggestedRecipientListViewOwner: one("ComposerSuggestedRecipientListView", {
            identifying: true,
            inverse: "composerSuggestedRecipientViews",
        }),
        suggestedRecipientInfo: one("SuggestedRecipientInfo", {
            identifying: true,
            inverse: "composerSuggestedRecipientViews",
        }),
    },
});
