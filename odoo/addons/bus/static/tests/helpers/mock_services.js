/** @odoo-module **/

import { presenceService } from "@bus/services/presence_service";

export function makeFakePresenceService(params = {}) {
    return {
        ...presenceService,
        start(env) {
            return {
                ...presenceService.start(env),
                ...params,
            };
        },
    };
}
