/** @odoo-module */

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";
import { SoundPlayer } from "./sound_player";

const soundEffects = {
    error: "/point_of_sale/static/src/sounds/error.wav",
    bell: "/point_of_sale/static/src/sounds/bell.wav",
};

export const soundService = {
    start() {
        const sounds = reactive({});
        let nextId = 0;
        registry.category("main_components").add("SoundPlayer", {
            Component: SoundPlayer,
            props: { sounds },
        });
        return {
            play(name) {
                const id = nextId++;
                sounds[id] = {
                    cleanup: () => delete sounds[id],
                    src: soundEffects[name],
                };
            },
        };
    },
};

registry.category("services").add("sound", soundService);
