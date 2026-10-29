/** @odoo-module */

import { describe, expect, microTick, mockFetch, test } from "@odoo/hoot";
import { parseUrl } from "../local_helpers";

describe(parseUrl(import.meta.url), () => {
    /** @type {BroadcastChannel} */
    let broadcastChannel;
    let objectURL;

    test("setup network values", async () => {
        expect(document.cookie).toBe("");

        document.cookie = "cids=4";
        document.title = "kek";

        expect(document.cookie).toBe("cids=4");
        expect(document.title).toBe("kek");
    });

    test("values are reset between test", async () => {
        expect(document.cookie).toBe("");
        expect(document.title).toBe("");
    });

    test("fetch with internal URLs works without mocking fetch", async () => {
        const blob = new Blob([JSON.stringify({ name: "coucou" })], {
            type: "application/json",
        });
        const blobUrl = URL.createObjectURL(blob);
        const blobResponse = await fetch(blobUrl).then((res) => res.json());
        const dataResponse = await fetch("data:text/html,<body></body>").then((res) => res.text());

        expect(blobResponse).toEqual({ name: "coucou" });
        expect(dataResponse).toBe("<body></body>");

        await expect(fetch("http://some.url")).rejects.toThrow(/fetch is not mocked/);
    });

    test("fetch with internal URLs should return default value", async () => {
        mockFetch(expect.step);

        const external = await fetch("http://some.url").then((res) => res.text());
        const internal = await fetch("/odoo").then((res) => res.text());
        const data = await fetch("data:text/html,<body></body>").then((res) => res.text());

        expect(external).toBe("null");
        expect(internal).toBe("null");
        expect(data).toBe("<body></body>");

        expect.verifySteps(["http://some.url", "/odoo", "data:text/html,<body></body>"]);
    });

    test("fetch JSON with blob URLs", async () => {
        mockFetch(expect.step);

        const blob = new Blob([JSON.stringify({ name: "coucou" })], {
            type: "application/json",
        });
        const blobUrl = URL.createObjectURL(blob);
        const response = await fetch(blobUrl);
        const json = await response.json();

        expect(json).toEqual({ name: "coucou" });

        expect.verifySteps([blobUrl]);
    });

    test("fetch with mocked blob URLs", async () => {
        mockFetch((input) => {
            expect.step(input);
            return "Some other content";
        });

        const blob = new Blob([JSON.stringify({ name: "coucou" })], {
            type: "application/json",
        });
        const blobUrl = URL.createObjectURL(blob);
        const response = await fetch(blobUrl);

        expect(response.headers).toEqual(new Headers([["Content-Type", "text/plain"]]));

        const text = await response.text();

        expect(text).toBe("Some other content");

        expect.verifySteps([blobUrl]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests object URLs cleanup.
    test("object URLs are revoked between tests: setup", async () => {
        objectURL = URL.createObjectURL(new Blob(["coucou"]));

        expect(await fetch(objectURL).then((res) => res.text())).toBe("coucou");
    });
    test("object URLs are revoked between tests: check", async () => {
        expect(objectURL).toMatch(/^blob:/);

        await expect(fetch(objectURL)).rejects.toThrow();
    });

    test("broadcast channels only reach other channels of the same name", async () => {
        const sender = new BroadcastChannel("hoot");
        const receiver = new BroadcastChannel("hoot");
        const other = new BroadcastChannel("other");
        const message = { value: 1 };
        sender.onmessage = () => expect.step("sender");
        receiver.onmessage = (ev) => {
            expect.step(`receiver:${ev.data.value}`);
            expect(ev.data).not.toBe(message);
        };
        other.onmessage = () => expect.step("other");

        expect(sender.name).toBe("hoot");

        sender.postMessage(message);

        // Messages are delivered asynchronously
        expect.verifySteps([]);

        await microTick();

        expect.verifySteps(["receiver:1"]);

        receiver.close();
        sender.postMessage(message);
        await microTick();

        expect.verifySteps([]);

        sender.close();

        expect(() => sender.postMessage(message)).toThrow(/closed/);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests broadcast channels cleanup.
    test("broadcast channels are closed between tests: setup", async () => {
        broadcastChannel = new BroadcastChannel("hoot");

        expect(broadcastChannel.name).toBe("hoot");
    });
    test("broadcast channels are closed between tests: check", async () => {
        broadcastChannel.onmessage = () => expect.step("message");
        new BroadcastChannel("hoot").postMessage("test");
        await microTick();

        expect.verifySteps([]);
        expect(() => broadcastChannel.postMessage("test")).toThrow(/closed/);
    });

    test.tags("secure");
    test("caches are always empty", async () => {
        await expect(caches.keys()).resolves.toEqual([]);
        await expect(caches.match("/route")).resolves.toBe(undefined);
        await expect(caches.delete("hoot")).resolves.toBe(false);
        await expect(caches.open("hoot")).rejects.toThrow(/not allowed/);
    });

    test("mock response with nested blobs", async () => {
        mockFetch(
            () =>
                new Blob(["some blob", new Blob([" with nested content"], { type: "text/plain" })])
        );

        const response = await fetch("/nestedBlob");
        const blob = await response.blob();
        const result = await blob.text();

        expect(result).toBe("some blob with nested content");
    });

    test("mock responses: array buffer", async () => {
        mockFetch(() => "some text");

        const response = await fetch("/arrayBuffer");
        const result = await response.arrayBuffer();

        expect(result).toBeInstanceOf(ArrayBuffer);
        expect(new TextDecoder("utf-8").decode(result)).toBe("some text");
    });

    test("mock responses: blob", async () => {
        mockFetch(() => "blob content");

        const response = await fetch("/blob");
        const result = await response.blob();

        expect(result).toBeInstanceOf(Blob);
        expect(result.size).toBe(12);

        const buffer = await result.arrayBuffer();
        expect(new TextDecoder("utf-8").decode(buffer)).toBe("blob content");
    });

    test("mock responses: bytes", async () => {
        mockFetch(() => "some text");

        const response = await fetch("/bytes");
        const result = await response.bytes();

        expect(result).toBeInstanceOf(Uint8Array);
        expect(new TextDecoder("utf-8").decode(result)).toBe("some text");
    });

    test("mock responses: formData", async () => {
        mockFetch(() => {
            const data = new FormData();
            data.append("name", "Frodo");
            return data;
        });

        const response = await fetch("/formData");
        const result = await response.formData();

        expect(result).toBeInstanceOf(FormData);
        expect(result.get("name")).toBe("Frodo");
    });

    test("mock responses: json", async () => {
        mockFetch(() => ({ json: "content" }));

        const response = await fetch("/json");
        const result = await response.json();

        expect(result).toEqual({ json: "content" });
    });

    test("mock responses: text", async () => {
        mockFetch(() => "some text");

        const response = await fetch("/text");
        const result = await response.text();

        expect(result).toBe("some text");
    });

    test("mock responses: stream", async () => {
        const encoder = new TextEncoder();
        mockFetch(
            () =>
                new Response(
                    new ReadableStream({
                        start(controller) {
                            controller.enqueue(encoder.encode("streamed content"));
                            controller.close();
                        },
                    })
                )
        );
        const response = await fetch("/stream");
        const { value } = await response.body.getReader().read();
        expect(response.headers.get("content-type")).toBe(null);
        expect(new TextDecoder().decode(value)).toBe("streamed content");
    });

    test("mock responses: error handling after reading body", async () => {
        mockFetch(() => "some text");

        const response = await fetch("/text");
        const responseClone = response.clone();
        const result = await response.text(); // read once

        expect(result).toBe("some text");

        // Rejects for every reader after body is used
        await expect(response.arrayBuffer()).rejects.toThrow(TypeError);
        await expect(response.blob()).rejects.toThrow(TypeError);
        await expect(response.bytes()).rejects.toThrow(TypeError);
        await expect(response.formData()).rejects.toThrow(TypeError);
        await expect(response.json()).rejects.toThrow(TypeError);
        await expect(response.text()).rejects.toThrow(TypeError);

        const cloneResult = await responseClone.text(); // read clone

        expect(cloneResult).toBe(result);

        // Clone rejects reader as well
        await expect(responseClone.text()).rejects.toThrow(TypeError);
    });
});
