/* @odoo-module */

import { registry } from "@web/core/registry";

export class GifPickerService {
    hasGifPickerFeature = false;
}

export const gifPickerService = {
    start(env, services) {
        return new GifPickerService(env, services);
    },
};

registry.category("services").add("discuss.gifPicker", gifPickerService);
