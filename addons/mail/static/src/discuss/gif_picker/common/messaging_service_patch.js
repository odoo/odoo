/* @odoo-module */

import { Messaging, messagingService } from "@mail/core/common/messaging_service";

import { patch } from "@web/core/utils/patch";

messagingService.dependencies.push("discuss.gifPicker");

/** @type {Messaging} */
const messagingPatch = {
    setup(env, services) {
        this._super(env, services);
        this.gifPickerService = services["discuss.gifPicker"];
    },
    initMessagingCallback(data) {
        this._super(data);
        this.gifPickerService.hasGifPickerFeature = data.hasGifPickerFeature;
    },
};

patch(Messaging.prototype, "GifPicker", messagingPatch);
