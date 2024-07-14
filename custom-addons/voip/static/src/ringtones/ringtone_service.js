/* @odoo-module */

import { registry } from "@web/core/registry";

export const ringtoneService = {
    start() {
        const audio = new window.Audio();
        const ringtones = {
            dial: {
                source: "/voip/static/src/ringtones/dialtone.mp3",
                volume: 0.7,
            },
            incoming: {
                source: "/voip/static/src/ringtones/incomingcall.mp3",
            },
            ringback: {
                source: "/voip/static/src/ringtones/ringbacktone.mp3",
            },
        };
        function play() {
            audio.currentTime = 0;
            audio.loop = true;
            audio.src = this.source;
            audio.volume = this.volume ?? 1;
            Promise.resolve(audio.play()).catch(() => {});
        }
        Object.values(ringtones).forEach((x) => Object.assign(x, { play }));
        return {
            ...ringtones,
            stopPlaying() {
                audio.pause();
                audio.currentTime = 0;
            },
        };
    },
};

registry.category("services").add("voip.ringtone", ringtoneService);
