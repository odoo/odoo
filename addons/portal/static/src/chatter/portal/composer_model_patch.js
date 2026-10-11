import { Composer } from "@mail/core/common/composer_model";
import { patchModel } from "@mail/model/export";

export const composerPatch = patchModel(Composer, {
    setup() {
        super.setup(...arguments);
        this.portalComment = false;
    },
});
