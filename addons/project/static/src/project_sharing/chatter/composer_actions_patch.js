import { ComposerAction } from "@mail/core/common/composer_actions";

import { patch } from "@web/core/utils/patch";

patch(ComposerAction.prototype, {
    _condition({ projectSharingId }) {
        if (this.id === "open-full-composer" && projectSharingId) {
            return false;
        }
        return super._condition(...arguments);
    },
});
