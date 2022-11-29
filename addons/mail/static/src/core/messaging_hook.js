/* @odoo-module */

import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 *  @returns {import("@mail/core/messaging_service").Messaging}
 */
export function useMessaging() {
    return useState(useService("mail.messaging"));
}

/**
 *  @returns {import("@mail/core/store_service").Store}
 */
export function useStore() {
    return useState(useService("mail.store"));
}
