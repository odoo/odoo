/* @odoo-module */

import { useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/**
 *  @returns {import("@mail/discuss/call/common/rtc_service").Rtc"}
 */
export function useRtc() {
    return useState(useService("discuss.rtc"));
}

/**
 *  @returns {import("@mail/discuss/call/common/rtc_server_service").Rtc"}
 */
export function useRtcServer() {
    return useState(useService("discuss.rtcServer"));
}
