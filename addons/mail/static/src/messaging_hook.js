/** @odoo-module */

import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export function useMessaging() {
    return useState(useService("mail.messaging"));
}
