/* @odoo-module */

import { reactive, useState } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class GifPickerService {
    hasGifPickerFeature = false;

    constructor(env, services) {
        /** @type {import("@mail/core/common/messaging_service").Messaging} */
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
    start(env, services) {
        /** @type {import('@mail/discuss/gif_picker/common/gif_picker_service').GifPickerService} */
        const gifPickerService = new reactive(new GifPickerService(env, services));
        gifPickerService.setup();
        return gifPickerService;
    },
};

/**
 * @returns {import('@mail/discuss/gif_picker/common/gif_picker_service').GifPickerService}
 */
export function useGifPickerService() {
    return useState(useService("discuss.gifPicker"));
}

registry.category("services").add("discuss.gifPicker", gifPickerService);
