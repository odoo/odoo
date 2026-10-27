import { onWillUnmount, signal } from "@odoo/owl";

import { CallPermissionDeniedDialog } from "@mail/discuss/call/common/call_permission_denied_dialog";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

export const DICTATION_STATE = Object.freeze({
    IDLE: "idle",
    LISTENING: "listening",
    FINISHING: "finishing",
});
/** @typedef {typeof DICTATION_STATE[keyof typeof DICTATION_STATE]} DictationState */

/**
 * Errors of the Web Speech API (`SpeechRecognitionErrorEvent.error`) that end
 * the dictation. "no-speech" is a silence, after which listening continues, and
 * "aborted" follows our own `abort()`.
 */
const FATAL_ERRORS = [
    "audio-capture",
    "language-not-supported",
    "network",
    "not-allowed",
    "service-not-allowed",
];
/** Scripts written without spaces between their words. */
const SPACELESS_SCRIPTS = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Thai}]/u;
/** Time to wait for the browser to end a stopped recognition, in milliseconds. */
const STOP_TIMEOUT = 3000;

function getSpeechRecognition() {
    return window.SpeechRecognition || window.webkitSpeechRecognition;
}

/** Joins the transcripts of two recognitions, which the browser does not separate. */
function joinTranscripts(before, after) {
    if (
        !before ||
        !after ||
        /\s$/.test(before) ||
        /^\s/.test(after) ||
        SPACELESS_SCRIPTS.test(before.at(-1)) ||
        SPACELESS_SCRIPTS.test(after[0])
    ) {
        return before + after;
    }
    return `${before} ${after}`;
}

export function isDictationSupported() {
    return !isMobileOS() && Boolean(getSpeechRecognition());
}

/**
 * Live speech-to-text of the browser, transcribing what is said until stopped.
 *
 * @param {Object} params
 * @param {() => void} params.onCancel called when unmounted while dictating
 * @param {(text: string) => void} params.onEnd called once stopped, with the whole transcript
 * @param {(text: string) => void} params.onTranscript called with the whole transcript so far
 * @param {import("@odoo/owl").Signal<HTMLElement>} [params.rootRef]
 */
export function useDictation({ onCancel, onEnd, onTranscript, rootRef }) {
    const dialog = useService("dialog");
    const notification = useService("notification");
    /** @type {import("@odoo/owl").Signal<DictationState>} */
    const state = signal(DICTATION_STATE.IDLE);
    /** Text of the results finalized by the previous recognitions of this dictation. */
    let committedText = "";
    /** @type {SpeechRecognition|undefined} */
    let recognition;
    let text = "";

    function startRecognition() {
        const SpeechRecognition = getSpeechRecognition();
        const current = new SpeechRecognition();
        recognition = current;
        current.continuous = true;
        current.interimResults = true;
        current.lang = user.lang;
        current.onresult = (ev) => {
            if (recognition !== current) {
                return;
            }
            let finalText = "";
            let interimText = "";
            for (const result of ev.results) {
                if (result.isFinal) {
                    finalText += result[0].transcript;
                } else {
                    interimText += result[0].transcript;
                }
            }
            text = joinTranscripts(committedText, finalText + interimText);
            onTranscript(text);
        };
        current.onerror = (ev) => {
            if (recognition !== current || !FATAL_ERRORS.includes(ev.error)) {
                return;
            }
            // so that the end of this recognition does not restart it
            state.set(DICTATION_STATE.FINISHING);
            if (["not-allowed", "service-not-allowed"].includes(ev.error)) {
                dialog.add(
                    CallPermissionDeniedDialog,
                    { permissionType: "microphone" },
                    { rootRef }
                );
            } else {
                notification.add(_t("Speech recognition is unavailable."), { type: "warning" });
            }
        };
        current.onend = () => {
            if (recognition !== current) {
                return;
            }
            // The browser ends the recognition on its own after a silence.
            if (state() === DICTATION_STATE.LISTENING) {
                committedText = text;
                startRecognition();
                return;
            }
            end();
        };
        try {
            current.start();
        } catch {
            end();
        }
    }

    function end() {
        recognition = undefined;
        state.set(DICTATION_STATE.IDLE);
        onEnd(text);
    }

    function start() {
        if (state() !== DICTATION_STATE.IDLE) {
            return;
        }
        committedText = "";
        text = "";
        state.set(DICTATION_STATE.LISTENING);
        startRecognition();
    }

    /** Stops listening: the pending results are still transcribed, then `onEnd` is called. */
    function stop() {
        if (state() !== DICTATION_STATE.LISTENING) {
            return;
        }
        state.set(DICTATION_STATE.FINISHING);
        const current = recognition;
        current.stop();
        // in case the browser never ends the recognition
        setTimeout(() => {
            if (recognition === current) {
                end();
                current.abort();
            }
        }, STOP_TIMEOUT);
    }

    /** Stops listening without calling `onEnd`, when unmounted while dictating. */
    function cancel() {
        if (state() === DICTATION_STATE.IDLE) {
            return;
        }
        const current = recognition;
        recognition = undefined;
        state.set(DICTATION_STATE.IDLE);
        current?.abort();
        onCancel();
    }

    onWillUnmount(cancel);
    return { start, state, stop };
}
