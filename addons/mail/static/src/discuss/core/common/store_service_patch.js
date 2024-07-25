import { Store } from "@mail/model/store";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    sortOnlineMembers(m1, m2) {
        return m1.persona.name?.localeCompare(m2.persona.name) || m1.id - m2.id;
    },
};

patch(Store.prototype, storeServicePatch);
