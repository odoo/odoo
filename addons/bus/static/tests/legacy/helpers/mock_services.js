/** @odoo-module alias=@bus/../tests/helpers/mock_services default=false */

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
