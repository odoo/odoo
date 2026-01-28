import { ComposerAction } from "@mail/core/common/composer_actions";

import { patch } from "@web/core/utils/patch";

patch(ComposerAction.prototype, {
    _condition({ owner }) {
        if (this.id === "open-full-composer" && owner.env.projectSharingId) {
            return false;
        }
        return super._condition(...arguments);
    },
});
