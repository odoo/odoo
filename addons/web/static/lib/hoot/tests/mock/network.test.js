/** @odoo-module */

import { after, describe, expect, mockFetch, test } from "@odoo/hoot";
import { parseUrl } from "../local_helpers";

/**
 * @param {Blob | MediaSource} obj
 */
function createObjectURL(obj) {
    const url = URL.createObjectURL(obj);
    after(() => URL.revokeObjectURL(url));
    return url;
}

describe(parseUrl(import.meta.url), () => {
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
        const blobUrl = createObjectURL(blob);
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
        const blobUrl = createObjectURL(blob);
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
        const blobUrl = createObjectURL(blob);
        const response = await fetch(blobUrl);

        expect(response.headers).toEqual(new Headers([["Content-Type", "text/plain"]]));

        const text = await response.text();

        expect(text).toBe("Some other content");

        expect.verifySteps([blobUrl]);
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
