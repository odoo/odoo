/** @odoo-module */

import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @returns {import("./pos_store").PosStore}
 */
export function usePos() {
    return useState(useService("pos"));
}
