import { Composer } from "@mail/core/common/composer_model";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.portalComment = false;
    },
});
