import { Composer } from "@mail/core/common/composer_model";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    portalComment: false,
});
