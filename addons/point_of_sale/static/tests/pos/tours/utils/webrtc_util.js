/* global posmodel */

import { patch } from "@web/core/utils/patch";
import { cookie } from "@web/core/browser/cookie";
import { session } from "@web/session";

// Helpers of the WebRTC tours. These tours run at the same time in several
// browsers (see `test_webrtc.py`), on the same PoS opened with `debug=webrtc`,
// and wait for each other through the WebRTC debug popup.

// Names of the devices, given by the tests (see `patchWebrtcForTests`). Their
// ids are `<name>.<tag of their session>`: the tours, which don't know the tags
// of the other devices, use the names. No "-" nor "." in them: the logs only
// show the part of the id before the first one.
export const T1 = "device1";
export const T2 = "device2";
export const T3 = "device3";

/** The name of a device, from its id. */
function deviceName(id) {
    return id?.split(".")[0];
}

// ----- Patches ----- //

// A reloaded page, or one restored from the back/forward cache, gets a new
// device id, as a real one gets a new uuid: kept in the session storage of the
// tab (see `reloadAs` and `backFromCacheAs`), it wins over the cookie.
const TEST_ID_KEY = "webrtc_test_id";

/**
 * Patches the WebRTC plugins for the tests:
 * - the device id comes from the `webrtc_test_id` cookie (or from `reloadAs`
 *   and `backFromCacheAs`),
 *   so that the tests know which device has the smaller id, i.e. sends the offer;
 * - the signaling messages being sent are kept, so that a tour can wait for them
 *   (see `waitSignalingSent`);
 * - the errors are only kept in the logs: `console.error` would fail the tour.
 *
 * Nothing from the PoS is imported, since some tours resume in the backend:
 * the plugins are patched once their module is loaded, if it ever is.
 */
export function patchWebrtcForTests() {
    whenModuleLoaded("@point_of_sale/app/webrtc/webrtc_plugin", ({ WebRtcPlugin }) =>
        patch(WebRtcPlugin.prototype, {
            setup() {
                super.setup(...arguments);
                this.pendingSignals = new Set();
            },
            newId() {
                const name = sessionStorage.getItem(TEST_ID_KEY) || cookie.get(TEST_ID_KEY);
                // The tag of the session, which the server checks.
                return name ? `${name}.${session.pos_webrtc_tag}` : super.newId(...arguments);
            },
            signal() {
                const promise = super.signal(...arguments);
                const remove = () => this.pendingSignals.delete(promise);
                this.pendingSignals.add(promise);
                promise.then(remove, remove);
                return promise;
            },
        })
    );
    whenModuleLoaded("@point_of_sale/app/webrtc/webrtc_log_plugin", ({ WebRtcLogPlugin }) =>
        patch(WebRtcLogPlugin.prototype, {
            logError(text, error, peer = null) {
                this.add("error", `${text}: ${error?.message || error}`, peer);
            },
        })
    );
}

function whenModuleLoaded(name, callback) {
    const module = odoo.loader.modules.get(name);
    if (module) {
        callback(module);
        return;
    }
    odoo.loader.bus.addEventListener("module-started", ({ detail }) => {
        if (detail.moduleName === name) {
            callback(detail.module);
        }
    });
}

// ----- Popup ----- //

export function openDebugPopup() {
    return {
        content: "Open the WebRTC debug popup",
        trigger: ".o-debug-widget-btn[data-tooltip='WebRTC debug']",
        run: "click",
    };
}

export function openTab(name) {
    return {
        content: `Open the ${name} tab`,
        trigger: `.modal .nav-link:contains(${name})`,
        run: "click",
    };
}

function connectedPeerSelector(peer) {
    return `.modal .o_webrtc_peer[data-id^='${peer}.'] .badge.text-bg-success:contains(connected)`;
}

/**
 * @param {Object} params
 * @param {string} params.type - type of the log (e.g. "signal", "message")
 * @param {string} [params.peer] - name of the other device
 * @param {string} [params.text] - exact text of the log
 * @param {string} [params.textStart] - start of the text of the log
 */
function logSelector({ type, peer, text, textStart }) {
    let selector = `.modal .o_webrtc_log[data-type='${type}']`;
    if (peer) {
        selector += `[data-peer^='${peer}.']`;
    }
    if (text) {
        selector += `[data-text='${text}']`;
    }
    if (textStart) {
        selector += `[data-text^='${textStart}']`;
    }
    return selector;
}

/**
 * Logs of the given type, read from the logger rather than from the popup: the
 * popup only shows a new log once rendered again.
 */
function getLogs(type) {
    return posmodel.webrtc.logger.logs().filter((log) => log.type === type);
}

// ----- Actions ----- //

function broadcastHi() {
    return [
        openTab("Actions"),
        {
            content: 'Broadcast "Hi"',
            trigger: ".modal button.control-button:contains(Broadcast):enabled",
            run: "click",
        },
    ];
}

/**
 * Broadcasts any text through the plugin (the popup button only sends "Hi").
 */
export function broadcast(text) {
    return {
        content: `Broadcast "${text}"`,
        trigger: ".modal",
        run: () => posmodel.webrtc.broadcast(text),
    };
}

/**
 * Announces the device again, with the button of the popup.
 */
export function announceAgain() {
    return [
        openTab("Actions"),
        {
            content: "Announce again",
            trigger: ".modal button.control-button:contains(Announce)",
            run: "click",
        },
        openTab("Logs"),
        {
            content: "Wait for the announce to be sent",
            trigger: logSelector({ type: "signal", text: "sent announce to all" }),
        },
    ];
}

/**
 * Cuts the device from the server: the bus closes its websocket, as when the
 * browser goes offline, and doesn't try to reconnect. The connections between
 * the devices don't go through the server. Only the `offline` event is
 * simulated: the server stays up, so that the device can come back to it
 * (see `reconnectServer`).
 */
export function cutServer() {
    return {
        content: "Cut the device from the server",
        trigger: ".modal",
        run: () =>
            new Promise((resolve) => {
                posmodel.webrtc.bus.addEventListener("BUS:DISCONNECT", resolve, { once: true });
                window.dispatchEvent(new Event("offline"));
            }),
    };
}

/**
 * Reconnects a device cut by `cutServer`, and waits for it to announce itself
 * again. The logs must have been cleared before.
 */
export function reconnectServer() {
    return [
        {
            content: "Reconnect the device to the server",
            trigger: ".modal",
            run: () => window.dispatchEvent(new Event("online")),
        },
        openTab("Logs"),
        {
            content: "Wait for the device to announce itself again",
            trigger: logSelector({ type: "signal", text: "sent announce to all" }),
            // The bus waits a few seconds before reconnecting once back online.
            timeout: 20000,
        },
    ];
}

/**
 * Reloads the page, which comes back with the device id `id`.
 */
export function reloadAs(id) {
    return {
        content: `Reload the page as ${id}`,
        trigger: ".modal",
        run: () => {
            sessionStorage.setItem(TEST_ID_KEY, id);
            window.location.reload();
        },
        expectUnloadPage: true,
    };
}

/**
 * Simulates leaving the page while the browser keeps it in its back/forward
 * cache: the page isn't unloaded, it only receives `pagehide`. Chrome never
 * caches the PoS (WebRTC, Serial API, `Cache-Control: no-store`): going back
 * reloads it. Other browsers, like Safari, might restore it.
 */
export function leaveToCache() {
    return {
        content: "Leave the page, kept in the back/forward cache",
        trigger: ".modal",
        run: () => window.dispatchEvent(new PageTransitionEvent("pagehide", { persisted: true })),
    };
}

/**
 * Simulates coming back to the page restored from the back/forward cache, which
 * comes back with the device id `id`.
 */
export function backFromCacheAs(id) {
    return {
        content: `Come back to the page, restored from the back/forward cache, as ${id}`,
        trigger: ".modal",
        run: () => {
            sessionStorage.setItem(TEST_ID_KEY, id);
            window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
        },
    };
}

export function clearLogs() {
    return [
        openTab("Logs"),
        {
            content: "Clear the logs",
            trigger: ".modal .o_webrtc_clear_logs:enabled",
            run: "click",
        },
        {
            content: "Wait for the logs to be cleared",
            trigger: ".modal:not(:has(.o_webrtc_log))",
        },
    ];
}

// ----- Waits ----- //

export function waitNoPeer() {
    return [
        openTab("Peers"),
        {
            content: "Wait for all the peers to be removed",
            trigger: ".modal:not(:has(.o_webrtc_peer))",
        },
    ];
}

export function waitPeersConnected(peers) {
    return [
        openTab("Peers"),
        ...peers.map((peer) => ({
            content: `Wait for ${peer} to be connected`,
            trigger: connectedPeerSelector(peer),
        })),
        // A peer sends "Hello world" when its data channel opens: once
        // received, the channel is open on both sides and nothing gets lost.
        openTab("Logs"),
        ...peers.map((peer) => ({
            content: `Wait for the data channel with ${peer} to be open`,
            trigger: logSelector({ type: "message", peer, textStart: 'received "Hello world' }),
        })),
    ];
}

/**
 * Waits for the announce of `peer` to be ignored, since this device is
 * already connected to it.
 */
export function waitAnnounceIgnored(peer) {
    return [
        openTab("Logs"),
        {
            content: `Wait for the announce of ${peer} to be ignored`,
            trigger: logSelector({
                type: "signal",
                text: `ignored announce from ${peer}: existing connection (connected)`,
            }),
        },
    ];
}

/**
 * Waits for the signaling messages being sent, e.g. the ones sent in reaction to
 * a message that was just received: they are only logged once sent.
 */
export function waitSignalingSent() {
    return {
        content: "Wait for the signaling messages being sent",
        trigger: ".modal",
        run: () => Promise.allSettled(posmodel.webrtc.pendingSignals),
    };
}

export function waitMessageFrom(peers, text) {
    return [
        openTab("Logs"),
        ...peers.map((peer) => ({
            content: `Wait for the "${text}" of ${peer}`,
            trigger: logSelector({
                type: "message",
                peer,
                text: `received "${text}" from ${peer}`,
            }),
        })),
    ];
}

/**
 * Waits for `peer` to be removed because it closed the data channel, while
 * `remaining` stay connected.
 */
export function waitPeerLeft(peer, remaining) {
    return [
        openTab("Peers"),
        {
            content: `Wait for ${peer} to be removed from the peers`,
            trigger: `.modal:not(:has(.o_webrtc_peer[data-id^='${peer}.']))`,
        },
        ...remaining.map((other) => ({
            content: `Check that ${other} is still connected`,
            trigger: connectedPeerSelector(other),
        })),
        openTab("Logs"),
        {
            content: `Check that ${peer} was removed because it said it leaves`,
            trigger: logSelector({ type: "peer", peer, text: "closed: left" }),
        },
    ];
}

// ----- Checks ----- //

/**
 * Checks that the peers are exactly `peers`, e.g. no ghost of a reloaded device.
 */
export function checkPeers(peers) {
    return {
        content: `Check that the peers are exactly ${peers.join(", ")}`,
        trigger: ".modal",
        run: () => {
            // Read from the plugin rather than from the popup, like `getLogs`.
            const ids = [...posmodel.webrtc.peerStates().keys()].map(deviceName);
            assertSameItems(ids, peers, "Peers");
        },
    };
}

/**
 * Checks that the connection to `peer` was kept since the logs were cleared:
 * still connected, never closed, and no new data channel (which would say
 * "Hello world" again).
 */
export function checkConnectionKept(peer) {
    return [
        openTab("Peers"),
        {
            content: `Check that ${peer} is still connected`,
            trigger: connectedPeerSelector(peer),
        },
        checkPeers([peer]),
        openTab("Logs"),
        {
            content: `Check that the connection to ${peer} was neither closed nor replaced`,
            trigger: ".modal",
            run: () => {
                const helloWorlds = getLogs("message").filter((log) =>
                    log.text.includes('"Hello world')
                );
                const texts = [...getLogs("peer"), ...helloWorlds].map((log) => log.text);
                if (texts.length) {
                    throw new Error(`Connection to ${peer} not kept: ${JSON.stringify(texts)}`);
                }
            },
        },
    ].flat();
}

function checkOneHiFromEachPeer(peers) {
    return [
        openTab("Logs"),
        {
            content: 'Check that exactly one "Hi" was received from each peer',
            trigger: logSelector({ type: "message" }),
            run: () => {
                const senders = getLogs("message")
                    .map((log) => ({ ...log, peer: deviceName(log.peer) }))
                    .filter((log) => log.text === `received "Hi" from ${log.peer}`)
                    .map((log) => log.peer);
                assertSameItems(senders, peers, '"Hi" senders');
            },
        },
    ];
}

/**
 * Checks the signaling messages sent and handled by this device, whatever
 * their order (e.g. "sent offer to device2").
 */
export function checkSignaling(expected) {
    return [
        openTab("Logs"),
        {
            content: "Check the signaling messages",
            trigger: expected.length ? logSelector({ type: "signal" }) : ".modal",
            run: () => {
                const texts = getLogs("signal").map((log) => log.text);
                assertSameItems(texts, expected, "Signaling messages");
            },
        },
    ];
}

function assertSameItems(actual, expected, what) {
    const sortedActual = JSON.stringify([...actual].sort());
    const sortedExpected = JSON.stringify([...expected].sort());
    if (sortedActual !== sortedExpected) {
        throw new Error(`${what}: expected ${sortedExpected}, got ${sortedActual}`);
    }
}

// ----- Tours ----- //

/**
 * Steps of one device connecting to the other ones, then saying "Hi". The
 * devices say "Hi" one after the other: each one waits for the "Hi" of the
 * devices in `hiAfter` before saying its own.
 *
 * @param {Object} params
 * @param {string[]} params.peers - names of the other devices
 * @param {string[]} params.hiAfter - ids of the devices saying "Hi" before this one
 */
export function connectAndSayHi({ peers, hiAfter }) {
    return [
        waitPeersConnected(peers),
        waitMessageFrom(hiAfter, "Hi"),
        broadcastHi(),
        waitMessageFrom(peers, "Hi"),
        checkOneHiFromEachPeer(peers),
    ].flat();
}

/**
 * Tour of one device connecting to the other ones, saying "Hi", then checking
 * its signaling.
 *
 * @param {Object} params - see `connectAndSayHi`, and:
 * @param {string[]} params.signaling - expected texts of the signaling logs
 */
export function deviceTour({ peers, hiAfter, signaling }) {
    return {
        steps: () =>
            [
                openDebugPopup(),
                connectAndSayHi({ peers, hiAfter }),
                checkSignaling(signaling),
            ].flat(),
    };
}
