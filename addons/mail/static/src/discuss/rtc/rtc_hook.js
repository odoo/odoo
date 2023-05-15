/** @odoo-module */

import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 *  @returns {import("@mail/discuss/rtc/rtc_service").Rtc"}
 */
export function useRtc() {
    return useState(useService("mail.rtc"));
}
