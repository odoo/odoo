import { ComposerAction } from "@mail/core/common/composer_actions";

import { patch } from "@web/core/utils/patch";

patch(ComposerAction.prototype, {
    _condition({ ancestors }) {
        if (this.id === "open-full-composer" && ancestors.projectSharingId) {
            return false;
        }
        return super._condition(...arguments);
    },
});
