import { registry } from "@web/core/registry";
import {
    T1,
    T2,
    T3,
    announceAgain,
    backFromCacheAs,
    broadcast,
    checkConnectionKept,
    checkPeers,
    checkSignaling,
    clearLogs,
    connectAndSayHi,
    cutServer,
    leaveToCache,
    openDebugPopup,
    openTab,
    patchWebrtcForTests,
    reconnectServer,
    reloadAs,
    deviceTour,
    waitAnnounceIgnored,
    waitMessageFrom,
    waitNoPeer,
    waitPeerLeft,
    waitPeersConnected,
    waitSignalingSent,
} from "@point_of_sale/../tests/pos/tours/utils/webrtc_util";

patchWebrtcForTests();

const tours = registry.category("web_tour.tours");

// ----- test_webrtc_smaller_first ----- //

// The device with the smaller id is opened first: it sends the offer when it
// receives the announce of the other one.
const SMALLER_FIRST_SIGNALING = {
    [T1]: [
        "sent announce to all",
        `received announce from ${T2} to all`,
        `sent offer to ${T2}`,
        `received answer from ${T2}`,
    ],
    [T2]: ["sent announce to all", `received offer from ${T1}`, `sent answer to ${T1}`],
};

tours.add(
    "test_webrtc_smaller_first_t1",
    deviceTour({ peers: [T2], hiAfter: [], signaling: SMALLER_FIRST_SIGNALING[T1] })
);
tours.add(
    "test_webrtc_smaller_first_t2",
    deviceTour({ peers: [T1], hiAfter: [T1], signaling: SMALLER_FIRST_SIGNALING[T2] })
);

// ----- test_webrtc_bigger_first ----- //

// The device with the bigger id is opened first: it answers the announce of
// the other one with its own, so that the newcomer sends the offer.
tours.add(
    "test_webrtc_bigger_first_t2",
    deviceTour({
        peers: [T1],
        hiAfter: [],
        signaling: [
            "sent announce to all",
            `received announce from ${T1} to all`,
            `sent announce to ${T1}`,
            `received offer from ${T1}`,
            `sent answer to ${T1}`,
        ],
    })
);
tours.add(
    "test_webrtc_bigger_first_t1",
    deviceTour({
        peers: [T2],
        hiAfter: [T2],
        signaling: [
            "sent announce to all",
            `received announce from ${T2}`,
            `sent offer to ${T2}`,
            `received answer from ${T2}`,
        ],
    })
);

// ----- test_webrtc_three_devices ----- //

// Three devices opened in the order of their ids: each pair connects once.
const THREE_SIGNALING = {
    [T1]: [
        "sent announce to all",
        `received announce from ${T2} to all`,
        `sent offer to ${T2}`,
        `received answer from ${T2}`,
        `received announce from ${T3} to all`,
        `sent offer to ${T3}`,
        `received answer from ${T3}`,
    ],
    [T2]: [
        "sent announce to all",
        `received offer from ${T1}`,
        `sent answer to ${T1}`,
        `received announce from ${T3} to all`,
        `sent offer to ${T3}`,
        `received answer from ${T3}`,
    ],
    [T3]: [
        "sent announce to all",
        `received offer from ${T1}`,
        `sent answer to ${T1}`,
        `received offer from ${T2}`,
        `sent answer to ${T2}`,
    ],
};

tours.add(
    "test_webrtc_three_t1",
    deviceTour({ peers: [T2, T3], hiAfter: [], signaling: THREE_SIGNALING[T1] })
);
tours.add(
    "test_webrtc_three_t2",
    deviceTour({ peers: [T1, T3], hiAfter: [T1], signaling: THREE_SIGNALING[T2] })
);
tours.add(
    "test_webrtc_three_t3",
    deviceTour({ peers: [T1, T2], hiAfter: [T1, T2], signaling: THREE_SIGNALING[T3] })
);

// ----- test_webrtc_leave ----- //

// Three devices say "Hi", then T2 leaves the PoS (as when its tab is closed):
// T1 and T3 remove it from their peers, and keep talking to each other.
// T1 and T3 say "Bye" once they received every "Hi", so that T2 only leaves
// once nothing it sent is still on the way.
function stayingDeviceTour({ self, other, hiAfter }) {
    return {
        steps: () =>
            [
                openDebugPopup(),
                connectAndSayHi({ peers: [T2, other], hiAfter }),
                broadcast("Bye"),
                waitPeerLeft(T2, [other]),
                broadcast("Still here"),
                waitMessageFrom([other], "Still here"),
                // Leaving triggers no signaling: same as three devices that just connect.
                checkSignaling(THREE_SIGNALING[self]),
            ].flat(),
    };
}

tours.add("test_webrtc_leave_t1", stayingDeviceTour({ self: T1, other: T3, hiAfter: [] }));
tours.add("test_webrtc_leave_t2", {
    steps: () =>
        [
            openDebugPopup(),
            connectAndSayHi({ peers: [T1, T3], hiAfter: [T1] }),
            checkSignaling(THREE_SIGNALING[T2]),
            waitMessageFrom([T1, T3], "Bye"),
            {
                content: "Leave the PoS",
                trigger: ".modal",
                run: () => window.location.assign("/odoo"),
                expectUnloadPage: true,
            },
            {
                content: "Wait for the backend",
                trigger: ".o_main_navbar",
            },
        ].flat(),
});
tours.add("test_webrtc_leave_t3", stayingDeviceTour({ self: T3, other: T1, hiAfter: [T1, T2] }));

// ----- test_webrtc_reload ----- //

// T2 says "Hi" to T1, then reloads the page: it comes back with a new id, as a
// real device gets a new uuid on each load. T1 keeps a single peer, the new
// T2 (no ghost of the old one), and they say "Hi" again. The new id is still
// bigger than T1, so T1 sends the offer again. T1 says "Bye" once it received
// the "Hi", so that T2 only reloads once nothing it sent is still on the way.
const T2_RELOADED = "device2b";

tours.add("test_webrtc_reload_t1", {
    steps: () =>
        [
            openDebugPopup(),
            connectAndSayHi({ peers: [T2], hiAfter: [] }),
            broadcast("Bye"),
            waitPeerLeft(T2, []),
            waitPeersConnected([T2_RELOADED]),
            checkPeers([T2_RELOADED]),
            broadcast("Hi"),
            waitMessageFrom([T2_RELOADED], "Hi"),
            checkSignaling([
                "sent announce to all",
                `received announce from ${T2} to all`,
                `sent offer to ${T2}`,
                `received answer from ${T2}`,
                `received announce from ${T2_RELOADED} to all`,
                `sent offer to ${T2_RELOADED}`,
                `received answer from ${T2_RELOADED}`,
            ]),
        ].flat(),
});
tours.add("test_webrtc_reload_t2", {
    steps: () =>
        [
            openDebugPopup(),
            connectAndSayHi({ peers: [T1], hiAfter: [T1] }),
            checkSignaling([
                "sent announce to all",
                `received offer from ${T1}`,
                `sent answer to ${T1}`,
            ]),
            waitMessageFrom([T1], "Bye"),
            reloadAs(T2_RELOADED),
            // The logs start over with the page.
            openDebugPopup(),
            connectAndSayHi({ peers: [T1], hiAfter: [] }),
            checkPeers([T1]),
            checkSignaling([
                "sent announce to all",
                `received offer from ${T1}`,
                `sent answer to ${T1}`,
            ]),
        ].flat(),
});

// ----- test_webrtc_back_forward_cache ----- //

// T2 says "Hi" to T1, leaves the page and comes back to it from the
// back/forward cache (simulated, Chrome never caches the PoS: see
// `leaveToCache`): the page isn't loaded again, but leaving closed its
// connections. It comes back with a new id, since T1 may not have noticed yet
// that the old connection is closed, and would ignore its announce. It
// reconnects to T1, and they say "Hi again". The new id is still bigger than
// T1, so T1 sends the offer again. T1 says "Bye" once it received the "Hi", so
// that T2 only leaves once nothing it sent is still on the way.
const T2_RESTORED = "device2b";

tours.add("test_webrtc_back_forward_cache_t1", {
    steps: () =>
        [
            openDebugPopup(),
            connectAndSayHi({ peers: [T2], hiAfter: [] }),
            broadcast("Bye"),
            waitPeerLeft(T2, []),
            waitPeersConnected([T2_RESTORED]),
            waitMessageFrom([T2_RESTORED], "Hi again"),
            checkPeers([T2_RESTORED]),
            broadcast("Hi again"),
            checkSignaling([
                "sent announce to all",
                `received announce from ${T2} to all`,
                `sent offer to ${T2}`,
                `received answer from ${T2}`,
                `received announce from ${T2_RESTORED} to all`,
                `sent offer to ${T2_RESTORED}`,
                `received answer from ${T2_RESTORED}`,
            ]),
        ].flat(),
});
tours.add("test_webrtc_back_forward_cache_t2", {
    steps: () =>
        [
            openDebugPopup(),
            connectAndSayHi({ peers: [T1], hiAfter: [T1] }),
            checkSignaling([
                "sent announce to all",
                `received offer from ${T1}`,
                `sent answer to ${T1}`,
            ]),
            waitMessageFrom([T1], "Bye"),
            leaveToCache(),
            waitNoPeer(),
            // The page keeps its logs: start over, to tell the new connection
            // from the old one.
            clearLogs(),
            backFromCacheAs(T2_RESTORED),
            {
                content: "Wait for the announce to be sent again",
                trigger:
                    ".modal .o_webrtc_log[data-type='signal'][data-text='sent announce to all']",
            },
            waitPeersConnected([T1]),
            broadcast("Hi again"),
            waitMessageFrom([T1], "Hi again"),
            checkPeers([T1]),
            checkSignaling([
                "sent announce to all",
                `received offer from ${T1}`,
                `sent answer to ${T1}`,
            ]),
        ].flat(),
});

// ----- test_webrtc_announce_again_* ----- //

// T1 and T2 connect (T1 opened first) and say "Hi", then `announcer` announces
// itself again, as it will when its websocket reconnects. `receiver` already
// has a healthy connection to it, and keeps it: no new offer, no announce back,
// no new data channel. They say "Hi again" over the kept connection.
// `receiver` says "Ready" once it cleared its logs, so that the logs of both
// devices only show what follows the second announce.
function announceAgainTours({ announcer, receiver }) {
    const hiAfter = (self) => (self === T2 ? [T1] : []);
    const receiverSignaling = [
        `received announce from ${announcer} to all`,
        `ignored announce from ${announcer}: existing connection (connected)`,
    ];
    return {
        [announcer]: {
            steps: () =>
                [
                    openDebugPopup(),
                    connectAndSayHi({ peers: [receiver], hiAfter: hiAfter(announcer) }),
                    checkSignaling(SMALLER_FIRST_SIGNALING[announcer]),
                    waitMessageFrom([receiver], "Ready"),
                    clearLogs(),
                    announceAgain(),
                    waitMessageFrom([receiver], "Hi again"),
                    checkConnectionKept(receiver),
                    broadcast("Hi again"),
                    checkSignaling(["sent announce to all"]),
                ].flat(),
        },
        [receiver]: {
            steps: () =>
                [
                    openDebugPopup(),
                    connectAndSayHi({ peers: [announcer], hiAfter: hiAfter(receiver) }),
                    checkSignaling(SMALLER_FIRST_SIGNALING[receiver]),
                    clearLogs(),
                    broadcast("Ready"),
                    {
                        content: `Wait for the announce of ${announcer}`,
                        trigger: `.modal .o_webrtc_log[data-type='signal'][data-text='${receiverSignaling[0]}']`,
                    },
                    // A reply to the announce would only be logged once sent.
                    waitSignalingSent(),
                    checkSignaling(receiverSignaling),
                    checkConnectionKept(announcer),
                    broadcast("Hi again"),
                    waitMessageFrom([announcer], "Hi again"),
                ].flat(),
        },
    };
}

// The bigger id announces itself again: the smaller one doesn't send a new offer.
const ANNOUNCE_AGAIN_BIGGER = announceAgainTours({ announcer: T2, receiver: T1 });
tours.add("test_webrtc_announce_again_bigger_t1", ANNOUNCE_AGAIN_BIGGER[T1]);
tours.add("test_webrtc_announce_again_bigger_t2", ANNOUNCE_AGAIN_BIGGER[T2]);

// The smaller id announces itself again: the bigger one doesn't announce itself
// back (which would make the smaller one send a new offer).
const ANNOUNCE_AGAIN_SMALLER = announceAgainTours({ announcer: T1, receiver: T2 });
tours.add("test_webrtc_announce_again_smaller_t1", ANNOUNCE_AGAIN_SMALLER[T1]);
tours.add("test_webrtc_announce_again_smaller_t2", ANNOUNCE_AGAIN_SMALLER[T2]);

// ----- test_webrtc_server_cut ----- //

// T1 and T2 connect and say "Hi", then both are cut from the server: they still
// talk to each other, since their connection doesn't go through it, and they
// keep it. Then T1 comes back to the server, followed by T2: each one announces
// itself again and ignores the announce of the other, and they keep talking
// over the same connection. T2 only gets the announce of T1 once back, from the
// notifications that the bus missed meanwhile.
// Each device clears its logs while the other one waits for it, so that no
// message of the other one gets cleared (see `announceAgainTours`).
function serverBackSignaling(other) {
    return [
        "sent announce to all",
        `received announce from ${other} to all`,
        `ignored announce from ${other}: existing connection (connected)`,
    ];
}

tours.add("test_webrtc_server_cut_t1", {
    steps: () =>
        [
            openDebugPopup(),
            connectAndSayHi({ peers: [T2], hiAfter: [] }),
            checkSignaling(SMALLER_FIRST_SIGNALING[T1]),
            waitMessageFrom([T2], "Cut"),
            clearLogs(),
            cutServer(),
            broadcast("Hi without server"),
            waitMessageFrom([T2], "Hi without server"),
            checkConnectionKept(T2),
            checkSignaling([]),
            waitMessageFrom([T2], "Checked"),
            clearLogs(),
            reconnectServer(),
            broadcast("Back"),
            waitAnnounceIgnored(T2),
            waitSignalingSent(),
            checkSignaling(serverBackSignaling(T2)),
            broadcast("Hi again"),
            waitMessageFrom([T2], "Hi again"),
            checkConnectionKept(T2),
        ].flat(),
});
tours.add("test_webrtc_server_cut_t2", {
    steps: () =>
        [
            openDebugPopup(),
            connectAndSayHi({ peers: [T1], hiAfter: [T1] }),
            checkSignaling(SMALLER_FIRST_SIGNALING[T2]),
            clearLogs(),
            cutServer(),
            broadcast("Cut"),
            waitMessageFrom([T1], "Hi without server"),
            broadcast("Hi without server"),
            checkConnectionKept(T1),
            checkSignaling([]),
            clearLogs(),
            broadcast("Checked"),
            waitMessageFrom([T1], "Back"),
            reconnectServer(),
            waitAnnounceIgnored(T1),
            waitSignalingSent(),
            checkSignaling(serverBackSignaling(T1)),
            broadcast("Hi again"),
            waitMessageFrom([T1], "Hi again"),
            checkConnectionKept(T1),
        ].flat(),
});

// ----- test_webrtc_alone ----- //

// A device alone: it announces itself, and has nobody to talk to.
tours.add("test_webrtc_alone", {
    steps: () =>
        [
            openDebugPopup(),
            openTab("Logs"),
            {
                content: "Wait for the announce to be sent",
                trigger:
                    ".modal .o_webrtc_log[data-type='signal'][data-text='sent announce to all']",
            },
            openTab("Peers"),
            {
                content: "Check that there is no peer",
                trigger: ".modal div:contains(No peer yet.)",
            },
            openTab("Actions"),
            {
                content: 'Check that "Hi" can\'t be broadcast',
                trigger: ".modal button.control-button:contains(Broadcast):disabled",
            },
            broadcast("Hi"),
            openTab("Logs"),
            {
                content: "Check that no message was sent or received",
                trigger: ".modal:has(.o_webrtc_log):not(:has(.o_webrtc_log[data-type='message']))",
            },
            checkSignaling(["sent announce to all"]),
        ].flat(),
});
