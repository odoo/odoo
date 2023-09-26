<<<<<<< HEAD
/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    foldStateCount: 0,
});
||||||| parent of 16d7f417311 (temp)
=======
/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "discuss/core/web", {
    foldStateCount: 0,
});
>>>>>>> 16d7f417311 (temp)
