import { StorePlugin } from "@mail/core/common/store_plugin";

import { Plugin, signal, usePlugin } from "@odoo/owl";

/** Identifies the annotation messages among the other call broadcasts. */
export const ANNOTATION_MESSAGE_TYPE = "screen_annotation";
export const ANNOTATION_PROTOCOL_VERSION = 1;
/** How long a point stays fully visible, then how long it takes to fade out (ms). */
export const INK_VISIBLE_MS = 2000;
export const INK_FADE_MS = 1000;
export const INK_LIFETIME_MS = INK_VISIBLE_MS + INK_FADE_MS;
/** Points are batched to keep the number of network messages low. */
export const SEND_INTERVAL_MS = 50;
/** Bounds on what a remote participant can make us store. */
export const MAX_POINTS_PER_MESSAGE = 64;
export const MAX_POINTS_PER_STROKE = 2000;
export const INK_COLORS = [
    "#e8384f",
    "#fd9a00",
    "#62d26f",
    "#4186e0",
    "#aa62e3",
    "#e362e3",
    "#20aaea",
    "#fd612c",
];

/**
 * @param {number} sessionId
 * @returns {string} a stable color, so each participant keeps the same ink
 */
export function getInkColor(sessionId) {
    return INK_COLORS[Math.abs(sessionId) % INK_COLORS.length];
}

function clamp01(value) {
    return Math.min(1, Math.max(0, value));
}

/**
 * Checks a message received from another participant before using it: it comes from the
 * network, so it is only trusted for its shape and bounds.
 *
 * @param {any} message
 * @returns {boolean}
 */
export function isValidAnnotationMessage(message) {
    if (
        !message ||
        message.type !== ANNOTATION_MESSAGE_TYPE ||
        message.version !== ANNOTATION_PROTOCOL_VERSION ||
        !Number.isInteger(message.screenSessionId) ||
        !Number.isInteger(message.strokeId) ||
        !Number.isInteger(message.seq) ||
        !Array.isArray(message.points) ||
        message.points.length % 2 !== 0 ||
        message.points.length > MAX_POINTS_PER_MESSAGE * 2
    ) {
        return false;
    }
    return message.points.every((value) => Number.isFinite(value));
}

/**
 * Keeps the vanishing ink drawn on the shared screens of the call, sends the local strokes to
 * the other participants and receives theirs.
 *
 * Points are stored in coordinates normalized to the shared video frame (0 to 1 on both axes),
 * so that a stroke lands on the same spot of the shared screen whatever the size and layout of
 * each participant's call view.
 */
export class ScreenAnnotationPlugin extends Plugin {
    /** @type {import("models").Store} */
    #store = usePlugin(StorePlugin);
    isActive = signal(false);
    /** @type {Map<number, Map<string, Object>>} screen session id -> stroke key -> stroke */
    strokesByScreen = new Map();
    /** @type {Map<string, number>} last sequence number received, per remote stroke */
    lastSeqByStroke = new Map();
    /** @type {Set<function(number): void>} */
    listeners = new Set();
    nextStrokeId = 1;
    pendingStroke = undefined;
    sendTimeout = undefined;

    get rtc() {
        return this.#store.rtc;
    }

    get store() {
        return this.#store;
    }

    /** Whether there is a shared screen in the call the user takes part in. */
    get hasSharedScreen() {
        return Boolean(
            this.rtc?.channel?.rtc_session_ids.some((session) => session.is_screen_sharing_on)
        );
    }

    /** Whether the pointer draws on the shared screens instead of clicking them. */
    get isDrawing() {
        return this.isActive() && this.hasSharedScreen;
    }

    toggle() {
        this.isActive.set(!this.isDrawing);
    }

    /**
     * @param {function(number): void} listener called with the id of the screen session whose
     *  ink changed
     * @returns {function(): void} unsubscribe
     */
    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    /**
     * @param {number} screenSessionId
     * @returns {Iterable<Object>} the strokes drawn on that screen
     */
    getStrokes(screenSessionId) {
        return this.strokesByScreen.get(screenSessionId)?.values() ?? [];
    }

    /**
     * Drops the points that have fully faded out.
     *
     * @param {number} now see `performance.now()`
     */
    prune(now) {
        for (const [screenSessionId, strokes] of this.strokesByScreen) {
            for (const [key, stroke] of strokes) {
                while (stroke.points.length && now - stroke.points[0].time > INK_LIFETIME_MS) {
                    stroke.points.shift();
                }
                if (!stroke.points.length && stroke.isEnded) {
                    strokes.delete(key);
                    this.lastSeqByStroke.delete(key);
                }
            }
            if (!strokes.size) {
                this.strokesByScreen.delete(screenSessionId);
            }
        }
    }

    /**
     * @param {number} screenSessionId
     * @param {number} x normalized to the shared frame
     * @param {number} y normalized to the shared frame
     */
    startLocalStroke(screenSessionId, x, y) {
        this.endLocalStroke();
        const selfSession = this.rtc?.selfSession;
        if (!selfSession) {
            return;
        }
        const strokeId = this.nextStrokeId++;
        this.pendingStroke = { screenSessionId, strokeId, seq: 0, points: [] };
        this._addPoint(screenSessionId, `${selfSession.id}:${strokeId}`, selfSession, x, y);
        this.pendingStroke.points.push(x, y);
        this._scheduleSend();
    }

    /**
     * @param {number} x normalized to the shared frame
     * @param {number} y normalized to the shared frame
     */
    addLocalPoint(x, y) {
        const selfSession = this.rtc?.selfSession;
        if (!this.pendingStroke || !selfSession) {
            return;
        }
        const { screenSessionId, strokeId } = this.pendingStroke;
        this._addPoint(screenSessionId, `${selfSession.id}:${strokeId}`, selfSession, x, y);
        this.pendingStroke.points.push(x, y);
        if (this.pendingStroke.points.length >= MAX_POINTS_PER_MESSAGE * 2) {
            this._flush();
        } else {
            this._scheduleSend();
        }
    }

    endLocalStroke() {
        if (!this.pendingStroke) {
            return;
        }
        const selfSession = this.rtc?.selfSession;
        const { screenSessionId, strokeId } = this.pendingStroke;
        this._flush({ isEnded: true });
        this.pendingStroke = undefined;
        const stroke = selfSession
            ? this.strokesByScreen.get(screenSessionId)?.get(`${selfSession.id}:${strokeId}`)
            : undefined;
        if (stroke) {
            stroke.isEnded = true;
        }
    }

    /**
     * Handles an annotation message of another participant.
     *
     * @param {number} senderId the rtc session id of the sender, as given by the network (not
     *  by the message content)
     * @param {any} message
     */
    receive(senderId, message) {
        if (!isValidAnnotationMessage(message)) {
            return;
        }
        const sessions = this._getMessageSessions(senderId, message);
        if (!sessions) {
            return;
        }
        const { senderSession, screenSession } = sessions;
        const key = `${senderId}:${message.strokeId}`;
        // The same message can arrive twice when a participant is reachable both through the
        // SFU and peer-to-peer.
        const last = this.lastSeqByStroke.get(key);
        if (last !== undefined && message.seq <= last) {
            return;
        }
        this.lastSeqByStroke.set(key, message.seq);
        for (let i = 0; i < message.points.length; i += 2) {
            this._addPoint(
                screenSession.id,
                key,
                senderSession,
                clamp01(message.points[i]),
                clamp01(message.points[i + 1])
            );
        }
        if (message.isEnded) {
            const stroke = this.strokesByScreen.get(screenSession.id)?.get(key);
            if (stroke) {
                stroke.isEnded = true;
            }
        }
        this._notify(screenSession.id);
    }

    /**
     * Only accepts ink from a participant of the user's call, about a screen that is currently
     * shared in that call.
     *
     * @param {number} senderId
     * @param {Object} message
     * @returns {{ senderSession: Object, screenSession: Object }|undefined}
     */
    _getMessageSessions(senderId, message) {
        const channel = this.rtc?.channel;
        const Session = this.#store["discuss.channel.rtc.session"];
        const senderSession = Session.get(senderId);
        const screenSession = Session.get(message.screenSessionId);
        if (
            !channel ||
            !senderSession?.channel?.eq(channel) ||
            !screenSession?.channel?.eq(channel) ||
            !screenSession.is_screen_sharing_on
        ) {
            return undefined;
        }
        return { senderSession, screenSession };
    }

    _addPoint(screenSessionId, key, authorSession, x, y) {
        let strokes = this.strokesByScreen.get(screenSessionId);
        if (!strokes) {
            strokes = new Map();
            this.strokesByScreen.set(screenSessionId, strokes);
        }
        let stroke = strokes.get(key);
        if (!stroke) {
            stroke = {
                authorId: authorSession.id,
                color: getInkColor(authorSession.id),
                name: authorSession.name,
                isEnded: false,
                points: [],
            };
            strokes.set(key, stroke);
        }
        if (stroke.points.length >= MAX_POINTS_PER_STROKE) {
            stroke.points.shift();
        }
        stroke.points.push({ x, y, time: performance.now() });
        this._notify(screenSessionId);
    }

    _notify(screenSessionId) {
        for (const listener of this.listeners) {
            listener(screenSessionId);
        }
    }

    _scheduleSend() {
        if (this.sendTimeout) {
            return;
        }
        this.sendTimeout = setTimeout(() => this._flush(), SEND_INTERVAL_MS);
    }

    _flush({ isEnded = false } = {}) {
        clearTimeout(this.sendTimeout);
        this.sendTimeout = undefined;
        const stroke = this.pendingStroke;
        if (!stroke || (!stroke.points.length && !isEnded)) {
            return;
        }
        this.send({
            type: ANNOTATION_MESSAGE_TYPE,
            version: ANNOTATION_PROTOCOL_VERSION,
            screenSessionId: stroke.screenSessionId,
            strokeId: stroke.strokeId,
            seq: ++stroke.seq,
            points: stroke.points.map((value) => Math.round(value * 10000) / 10000),
            isEnded,
        });
        stroke.points = [];
    }

    /**
     * @param {Object} message JSON serializable
     */
    send(message) {
        this.rtc?.network?.broadcast(message);
    }
}
