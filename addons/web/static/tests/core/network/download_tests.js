/** @odoo-module */
import { browser } from "@web/core/browser/browser";
import { makeDeferred, patchWithCleanup } from "../../helpers/utils";
import { download } from "@web/core/network/download";
import { makeMockXHR } from "../../helpers/mock_services";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc_service";
import { registerCleanup } from "../../helpers/cleanup";

QUnit.module("download", (hooks) => {
    QUnit.test("handles connection error when behind a server", async (assert) => {
        assert.expect(1);

        function send() {
            this.status = 502;
            this.response = {
                type: "text/html",
            };
        }
        const MockXHR = makeMockXHR("", send);

        patchWithCleanup(browser, { XMLHttpRequest: MockXHR });

        let error;
        try {
            await download({
                data: {},
                url: "/some_url",
            });
        } catch (e) {
            error = e;
        }

        assert.ok(error instanceof ConnectionLostError);
    });

    QUnit.test("handles connection error when network unavailable", async (assert) => {
        assert.expect(1);

        async function send() {
            return Promise.reject();
        }
        const MockXHR = makeMockXHR("", send);

        patchWithCleanup(browser, { XMLHttpRequest: MockXHR });

        let error;
        try {
            await download({
                data: {},
                url: "/some_url",
            });
        } catch (e) {
            error = e;
        }

        assert.ok(error instanceof ConnectionLostError);
    });

    QUnit.test("handles business error from server", async (assert) => {
        assert.expect(4);

        const serverError = {
            code: 200,
            data: {
                name: "odoo.exceptions.RedirectWarning",
                arguments: ["Business Error Message", "someArg"],
                message: "Business Error Message",
            },
            message: "Odoo Server Error",
        };

        async function send() {
            this.status = 200;
            this.response = new Blob([JSON.stringify(serverError)], { type: "text/html" });
        }
        const MockXHR = makeMockXHR("", send);

        patchWithCleanup(browser, { XMLHttpRequest: MockXHR });

        let error;
        try {
            await download({
                data: {},
                url: "/some_url",
            });
        } catch (e) {
            error = e;
        }

        assert.ok(error instanceof RPCError);
        assert.strictEqual(error.data.name, serverError.data.name);
        assert.strictEqual(error.data.message, serverError.data.message);
        assert.deepEqual(error.data.arguments, serverError.data.arguments);
    });

    QUnit.test("handles arbitrary error", async (assert) => {
        assert.expect(3);

        const serverError = /* xml */ `<html><body><div>HTML error message</div></body></html>`;

        async function send() {
            this.status = 200;
            this.response = new Blob([JSON.stringify(serverError)], { type: "text/html" });
        }
        const MockXHR = makeMockXHR("", send);

        patchWithCleanup(browser, { XMLHttpRequest: MockXHR });

        let error;
        try {
            await download({
                data: {},
                url: "/some_url",
            });
        } catch (e) {
            error = e;
        }

        assert.ok(error instanceof RPCError);
        assert.strictEqual(error.message, "Arbitrary Uncaught Python Exception");
        assert.strictEqual(error.data.debug.trim(), `200` + `\n` + `HTML error message`);
    });

    QUnit.test("handles success download", async (assert) => {
        // This test relies on a implementation detail of the lowest layer of download
        // That is, a link will be created with the download attribute
        assert.expect(8);

        async function send(data) {
            assert.ok(data instanceof FormData);
            assert.strictEqual(data.get("someKey"), "someValue");
            assert.ok(data.has("token"));
            assert.ok(data.has("csrf_token"));

            this.status = 200;
            this.response = new Blob(["some plain text file"], { type: "text/plain" });
        }
        const MockXHR = makeMockXHR("", send);

        patchWithCleanup(browser, { XMLHttpRequest: MockXHR });

        assert.containsNone(document.body, "a[download]");

        const prom = makeDeferred();

        // This part asserts the implementation detail in question
        const downloadOnClick = (ev) => {
            const target = ev.target;
            if (target.tagName === "A" && "download" in target.attributes) {
                ev.preventDefault();
                assert.ok(target.href.startsWith("blob:"));
                assert.step("file downloaded");
                document.removeEventListener("click", downloadOnClick);
                prom.resolve();
            }
        };

        document.addEventListener("click", downloadOnClick);
        // safety first: do not pollute window
        registerCleanup(() => document.removeEventListener("click", downloadOnClick));
        download({ data: { someKey: "someValue" }, url: "/some_url" });
        await prom;
        assert.verifySteps(["file downloaded"]);
    });
});
