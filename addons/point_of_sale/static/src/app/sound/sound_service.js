/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

registry
    .category("sounds")
    .add("error", "/point_of_sale/static/src/sounds/error.wav")
    .add("bell", "/point_of_sale/static/src/sounds/bell.wav");

export const soundService = {
    start() {
        return {
            play(name) {
                const src = registry.category("sounds").get(name);
                const audio = new browser.Audio(src);
                audio.play();
            },
        };
    },
};

registry.category("services").add("sound", soundService);
