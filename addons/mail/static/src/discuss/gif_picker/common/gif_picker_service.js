/* @odoo-module */

import { reactive, useState } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class GifPickerService {
    hasGifPickerFeature = false;

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.messagingService = services["mail.messaging"];
    }

    setup() {
        this.messagingService.isReady.then(({ hasGifPickerFeature }) => {
            Object.assign(this, { hasGifPickerFeature });
        });
    }
}

export const gifPickerService = {
    dependencies: ["mail.messaging"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const gifPickerService = reactive(new GifPickerService(env, services));
        gifPickerService.setup();
        return gifPickerService;
    },
};

export function useGifPickerService() {
    return useState(useService("discuss.gifPicker"));
}

registry.category("services").add("discuss.gifPicker", gifPickerService);
