/** @odoo-module */

import { Component, reactive, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

registry
    .category("sounds")
    .add("error", "/point_of_sale/static/src/sounds/error.wav")
    .add("bell", "/point_of_sale/static/src/sounds/bell.wav");

class SoundContainer extends Component {
    static template = xml`<t t-foreach="props.sounds" t-as="sound" t-key="sound">
        <audio autoplay="true" t-att-src="sound_value.src" t-on-ended="sound_value.cleanup" t-on-error="() => onError(sound_value)"/>
    </t>`;
    static props = {
        sounds: Object,
    };
    onError(sound) {
        sound.cleanup();
        const err = new Error(`Couldn't load sound at "${sound.src}"`);
        throw err;
    }
}

export const soundService = {
    start() {
        let soundId = 0;
        const sounds = reactive({});
        registry.category("main_components").add("SoundContainer", {
            Component: SoundContainer,
            props: { sounds },
        });
        return {
            play(name) {
                const id = soundId++;
                sounds[id] = {
                    src: registry.category("sounds").get(name),
                    cleanup: () => delete sounds[id],
                };
            },
        };
    },
};

registry.category("services").add("sound", soundService);
