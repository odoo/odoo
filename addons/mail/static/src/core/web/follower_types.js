import { t } from "@odoo/owl";

/** @param {import("models").Store} store */
export const onFollowerChangedType = (store) =>
    t.function([t.object({ thread: t.instanceOf(store["mail.thread"]) })]);
