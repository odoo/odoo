import { Record } from "@mail/core/common/record";
import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.rtc = Record.one("Rtc", {
            compute() {
                return {};
            },
        });
    },
    onStarted() {
        super.onStarted(...arguments);
        this.rtc.start();
    },
};
patch(Store.prototype, StorePatch);
