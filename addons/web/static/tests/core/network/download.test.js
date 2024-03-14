import { after, describe, expect, test } from "@odoo/hoot";
import { Deferred, mockFetch } from "@odoo/hoot-mock";
import { patchTranslations } from "@web/../tests/web_test_helpers";

import { download } from "@web/core/network/download";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";

describe.current.tags("headless");

test("handles connection error when behind a server", async () => {
    const restoreFetch = mockFetch(() => new Response("", { status: 502 }));
    after(restoreFetch);
    const error = new ConnectionLostError("/some_url");
    await expect(download({ data: {}, url: "/some_url" })).rejects.toThrow(error);
});

test("handles connection error when network unavailable", async () => {
    const restoreFetch = mockFetch(() => Promise.reject());
    after(restoreFetch);
    const error = new ConnectionLostError("/some_url");
    await expect(download({ data: {}, url: "/some_url" })).rejects.toThrow(error);
});

test("handles business error from server", async () => {
    const serverError = {
        code: 200,
        data: {
            name: "odoo.exceptions.RedirectWarning",
            arguments: ["Business Error Message", "someArg"],
            message: "Business Error Message",
        },
        message: "Odoo Server Error",
    };

    const restoreFetch = mockFetch(() => {
        const blob = new Blob([JSON.stringify(serverError)], { type: "text/html" });
        return new Response(blob, { status: 200 });
    });
    after(restoreFetch);

    let error = null;
    try {
        await download({
            data: {},
            url: "/some_url",
        });
    } catch (e) {
        error = e;
    }
    expect(error).toBeInstanceOf(RPCError);
    expect(error.data).toEqual(serverError.data);
});

test("handles arbitrary error", async () => {
    const serverError = /* xml */ `<html><body><div>HTML error message</div></body></html>`;

    const restoreFetch = mockFetch(() => {
        const blob = new Blob([JSON.stringify(serverError)], { type: "text/html" });
        return new Response(blob, { status: 200 });
    });
    after(restoreFetch);

    let error = null;
    try {
        await download({
            data: {},
            url: "/some_url",
        });
    } catch (e) {
        error = e;
    }

    expect(error).toBeInstanceOf(RPCError);
    expect(error.message).toBe("Arbitrary Uncaught Python Exception");
    expect(error.data.debug.trim()).toBe("200\nHTML error message");
});

test("handles success download", async () => {
    patchTranslations();
    // This test relies on a implementation detail of the lowest layer of download
    // That is, a link will be created with the download attribute

    const restoreFetch = mockFetch((_, { body }) => {
        expect(body).toBeInstanceOf(FormData);
        expect(body.get("someKey")).toBe("someValue");
        expect(body.has("token")).toBe(true);
        expect(body.has("csrf_token")).toBe(true);
        expect.step("fetching file");

        const blob = new Blob(["some plain text file"], { type: "text/plain" });
        return new Response(blob, { status: 200 });
    });
    after(restoreFetch);

    const deferred = new Deferred();

    // This part asserts the implementation detail in question
    const downloadOnClick = (ev) => {
        const target = ev.target;
        if (target.tagName === "A" && "download" in target.attributes) {
            ev.preventDefault();

            expect(target.href).toMatch(/^blob:/);
            expect.step("file downloaded");
            document.removeEventListener("click", downloadOnClick);
            deferred.resolve();
        }
    };

    document.addEventListener("click", downloadOnClick);
    after(() => document.removeEventListener("click", downloadOnClick));

    expect("a[download]").toHaveCount(0); // link will be added by download
    download({ data: { someKey: "someValue" }, url: "/some_url" });
    await deferred;
    expect(["fetching file", "file downloaded"]).toVerifySteps();
});
