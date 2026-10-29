/** @odoo-module */

import { after, describe, expect, microTick, test, watchListeners } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { EventBus } from "@odoo/owl";
import { mountForTest, parseUrl } from "../local_helpers";

/**
 * @param {string} name
 * @returns {Promise<IDBDatabase>}
 */
function openDatabase(name) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(name);
        request.onupgradeneeded = () => expect.step(`upgrade:${name}`);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

describe(parseUrl(import.meta.url), () => {
    class TestBus extends EventBus {
        addEventListener(type) {
            expect.step(`addEventListener:${type}`);
            return super.addEventListener(...arguments);
        }

        removeEventListener() {
            throw new Error("Cannot remove event listeners");
        }
    }

    /** @type {HTMLAudioElement} */
    let audioElement;
    let observedNode;
    /** @type {RTCPeerConnection} */
    let peerConnection;
    let testBus;

    test("elementFromPoint and elementsFromPoint should be mocked", async () => {
        await mountForTest(/* xml */ `
            <div class="oui" style="position: absolute; left: 10px; top: 10px; width: 250px; height: 250px;">
                Oui
            </div>
        `);

        expect(".oui").toHaveRect({
            x: 10,
            y: 10,
            width: 250,
            height: 250,
        });

        const div = queryOne(".oui");
        expect(document.elementFromPoint(11, 11)).toBe(div);
        expect(document.elementsFromPoint(11, 11)).toEqual([
            div,
            document.body,
            document.documentElement,
        ]);

        expect(document.elementFromPoint(9, 9)).toBe(document.body);
        expect(document.elementsFromPoint(9, 9)).toEqual([document.body, document.documentElement]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests event listeners cleanup.
    test("event listeners are properly removed: setup", async () => {
        const callback = () => expect.step("callback");

        testBus = new TestBus();

        expect.verifySteps([]);

        after(watchListeners());

        testBus.addEventListener("some-event", callback);
        testBus.trigger("some-event");

        expect.verifySteps(["addEventListener:some-event", "callback"]);
    });
    test("event listeners are properly removed: check", async () => {
        testBus.trigger("some-event");

        expect.verifySteps([]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests event listeners cleanup.
    test("event listeners with options are properly removed: setup", async () => {
        after(watchListeners());

        const controller = new AbortController();
        window.addEventListener("hoot-event", () => expect.step("capture"), true);
        window.addEventListener("hoot-event", () => expect.step("signal"), {
            signal: controller.signal,
        });
        window.dispatchEvent(new Event("hoot-event"));

        expect.verifySteps(["capture", "signal"]);

        controller.abort();
        window.dispatchEvent(new Event("hoot-event"));

        expect.verifySteps(["capture"]);
    });
    test("event listeners with options are properly removed: check", async () => {
        window.dispatchEvent(new Event("hoot-event"));

        expect.verifySteps([]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests observers cleanup.
    test("observers are disconnected between tests: setup", async () => {
        expect(MutationObserver.name).toBe("MutationObserver");

        observedNode = document.createElement("div");
        const observer = new MutationObserver(() => expect.step("mutation"));
        observer.observe(observedNode, { attributes: true });
        observedNode.setAttribute("data-value", "1");
        await microTick();

        expect.verifySteps(["mutation"]);
    });
    test("observers are disconnected between tests: check", async () => {
        observedNode.setAttribute("data-value", "2");
        await microTick();

        expect.verifySteps([]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests IndexedDB cleanup.
    test("IndexedDB databases are deleted between tests: setup", async () => {
        await openDatabase("hoot_test_db");
        await openDatabase("hoot_test_db");

        expect.verifySteps(["upgrade:hoot_test_db"]);

        // Left opening at the end of the test
        indexedDB.open("hoot_test_pending_db");
    });
    test("IndexedDB databases are deleted between tests: check", async () => {
        await openDatabase("hoot_test_db");
        await openDatabase("hoot_test_pending_db");

        expect.verifySteps(["upgrade:hoot_test_db", "upgrade:hoot_test_pending_db"]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests media elements cleanup.
    test("media elements are paused between tests: setup", async () => {
        audioElement = new Audio();
        audioElement.loop = true;
        audioElement.play().catch(() => {});

        expect(audioElement.paused).toBe(false);
    });
    test("media elements are paused between tests: check", async () => {
        expect(audioElement.paused).toBe(true);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests peer connections cleanup.
    test("peer connections are closed between tests: setup", async () => {
        peerConnection = new RTCPeerConnection();

        expect(peerConnection.signalingState).toBe("stable");
    });
    test("peer connections are closed between tests: check", async () => {
        expect(peerConnection.signalingState).toBe("closed");
    });
});
