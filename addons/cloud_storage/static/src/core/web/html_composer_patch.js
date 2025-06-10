import { HtmlComposer } from "@mail/core/web/html_composer";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(HtmlComposer.prototype, {
    setup() {
        super.setup();
        this.cloudStorageUsable = session.cloud_storage_min_file_size !== undefined;
    },
});
