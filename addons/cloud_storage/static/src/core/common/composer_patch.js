import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(Composer.prototype, {
    get cloudStorageUsable() {
        return (
            !this.thread?.channel?.ai_agent_id && // ai_agent (enterprise) does not support url files
            session.cloud_storage_min_file_size !== undefined
        );
    },
});
