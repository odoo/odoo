import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.cloudStorageUsable = session.cloud_storage_min_file_size !== undefined;
    },
});
