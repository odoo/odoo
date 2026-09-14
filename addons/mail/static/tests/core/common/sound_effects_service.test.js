import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { browser } from "@web/core/browser/browser";
import { getService, patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

/**
 * Audio mock behaving like Safari on iOS/iPadOS: ogg is not supported, media is
 * only loaded on playback, and seeking before that throws.
 */
class AudioMock {
    HAVE_NOTHING = 0;
    readyState = 0;
    paused = true;
    loop = false;
    volume = 1;
    src = "";
    /** forces seeking to be refused, whatever the readyState */
    seekAlwaysThrows = false;
    _currentTime = 0;

    get currentTime() {
        return this._currentTime;
    }

    set currentTime(value) {
        if (this.seekAlwaysThrows || this.readyState === this.HAVE_NOTHING) {
            throw new DOMException("The object is in an invalid state.", "InvalidStateError");
        }
        this._currentTime = value;
    }

    canPlayType() {
        return "";
    }

    pause() {
        this.paused = true;
    }

    play() {
        this.paused = false;
        return Promise.resolve();
    }
}

/**
 * @returns {[import("@mail/core/common/sound_effects_service").SoundEffects, AudioMock]}
 */
function playNewMessage() {
    const soundEffects = getService("mail.sound_effects");
    expect(() => soundEffects.play("new-message")).not.toThrow();
    return [soundEffects, soundEffects.soundEffects["new-message"].audio];
}

test("sound effect is played on iOS, where seeking before load throws", async () => {
    await start();
    patchWithCleanup(browser, { Audio: AudioMock });
    const [, audio] = playNewMessage();
    expect(audio.src).toMatch(/\/mail\/static\/src\/audio\/new-message\.mp3$/);
    expect(audio.readyState).toBe(audio.HAVE_NOTHING);
    expect(audio.paused).toBe(false);
});

test("sound effect is played even when seeking is refused", async () => {
    await start();
    patchWithCleanup(browser, { Audio: AudioMock });
    const [soundEffects, audio] = playNewMessage();
    audio.readyState = 4; // HAVE_ENOUGH_DATA
    audio.seekAlwaysThrows = true;
    audio.pause();
    expect(() => soundEffects.play("new-message")).not.toThrow();
    expect(audio.paused).toBe(false);
});

test("sound effect is rewound when replayed mid-playback", async () => {
    await start();
    patchWithCleanup(browser, { Audio: AudioMock });
    const [soundEffects, audio] = playNewMessage();
    audio.readyState = 4; // HAVE_ENOUGH_DATA
    audio.currentTime = 1.5;
    soundEffects.play("new-message");
    expect(audio.currentTime).toBe(0);
    expect(audio.paused).toBe(false);
});

test("stopping a sound effect that cannot be seeked does not throw", async () => {
    await start();
    patchWithCleanup(browser, { Audio: AudioMock });
    const [soundEffects, audio] = playNewMessage();
    expect(() => soundEffects.stop("new-message")).not.toThrow();
    expect(audio.paused).toBe(true);
});
