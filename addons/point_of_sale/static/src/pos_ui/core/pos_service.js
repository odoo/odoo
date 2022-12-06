/** @odoo-module */

import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { PosStore } from "./pos_store";

const posService = {
    dependencies: ["number_buffer"],
    start(env, { number_buffer: numberBuffer }) {
        return new PosStore({ numberBuffer });
    },
};

registry.category("services").add("pos", posService);

export function usePos() {
    return useState(useService("pos"));
}
