import {
    click,
    defineMailModels,
    editInput,
    onRpcAfter,
    onRpcBefore,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { insertTextInComposer } from "@mail/../tests/mail_test_helpers_composer";

import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, press, waitFor, waitForNone } from "@odoo/hoot-dom";

import { onRpc } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

describe.current.tags("desktop");
defineMailModels();

test("post a message whose cloud upload fails", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patch(session, { cloud_storage_min_file_size: 0, cloud_storage_unsupported_models: [] });
    onRpcAfter("/mail/attachment/upload", async (response) => ({
        ...(await response),
        upload_info: { method: "PUT", url: "/cloud_storage/upload", response_status: 201 },
    }));
    const { promise: cloudUploadPromise, reject: failCloudUpload } = Promise.withResolvers();
    onRpc("/cloud_storage/upload", () => {
        expect.step("cloud_upload");
        return cloudUploadPromise;
    });
    onRpcBefore("/mail/message/post", (args) =>
        expect.step(
            `message_post: ${args.post_data.body} - ${args.post_data.attachment_ids.length} attachment(s)`
        )
    );
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer input[type=file]:count(1)");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await insertTextInComposer(".o-mail-Composer", "Dummy Message");
    await editInput(document.body, ".o-mail-Composer input[type=file]", [file]);
    await expect.waitForSteps(["cloud_upload"]);
    await press("Enter");
    await waitFor(
        ".o-mail-Message:has(:text('Dummy Message')) .o-mail-AttachmentContainer.o-isUploading:count(1)"
    );
    expect.verifySteps([]);
    failCloudUpload(new Error("Cloud storage unreachable"));
    await waitFor(".o_notification:text('Cloud storage error'):count(1)");
    await expect.waitForSteps(["message_post: <div>Dummy Message</div> - 0 attachment(s)"]);
    await waitFor(".o-mail-Message:has(:text('Dummy Message')):count(1)");
    await waitForNone(".o-mail-Message .o-mail-AttachmentContainer");
});

test("finished cloud uploads keep their size in the progress of a pending message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patch(session, { cloud_storage_min_file_size: 0, cloud_storage_unsupported_models: [] });
    onRpcAfter("/mail/attachment/upload", async (response) => ({
        ...(await response),
        upload_info: { method: "PUT", url: "/cloud_storage/upload", response_status: 201 },
    }));
    const resolveCloudUploads = [];
    onRpc("/cloud_storage/upload", () => {
        expect.step("cloud_upload");
        const { promise, resolve } = Promise.withResolvers();
        resolveCloudUploads.push(resolve);
        return promise;
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer input[type=file]:count(1)");
    const smallFile = new File(["hello, world"], "small.txt", { type: "text/plain" });
    await editInput(document.body, ".o-mail-Composer input[type=file]", [smallFile]);
    await expect.waitForSteps(["cloud_upload"]);
    const largeFile = new File(["hello, world".repeat(3)], "large.txt", { type: "text/plain" });
    await editInput(document.body, ".o-mail-Composer input[type=file]", [largeFile]);
    await expect.waitForSteps(["cloud_upload"]);
    await press("Enter");
    await waitFor(".o-mail-Message-uploadProgress[title='Uploading… 0%']:count(1)");
    resolveCloudUploads[0](new Response(null, { status: 201 }));
    await waitFor(
        ".o-mail-Message .o-mail-AttachmentContainer:not(.o-isUploading):contains(small.txt):count(1)"
    );
    await waitFor(".o-mail-Message-uploadProgress[title='Uploading… 25%']:count(1)");
});

test("cancel the cloud upload of a pending message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patch(session, { cloud_storage_min_file_size: 0, cloud_storage_unsupported_models: [] });
    onRpcAfter("/mail/attachment/upload", async (response) => ({
        ...(await response),
        upload_info: { method: "PUT", url: "/cloud_storage/upload", response_status: 201 },
    }));
    onRpc("/cloud_storage/upload", () => {
        expect.step("cloud_upload");
        return new Promise(() => {}); // simulates a cloud upload that never completes
    });
    onRpcBefore("/mail/attachment/delete", () => expect.step("attachment_delete"));
    onRpcBefore("/mail/message/post", () => expect.step("message_post"));
    patch(XMLHttpRequest.prototype, {
        abort() {
            super.abort();
            this.onabort?.(); // notified by browsers, unlike the mocked request
        },
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer input[type=file]:count(1)");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await editInput(document.body, ".o-mail-Composer input[type=file]", [file]);
    await expect.waitForSteps(["cloud_upload"]);
    await press("Enter");
    await waitFor(".o-mail-Message .o-mail-AttachmentContainer.o-isUploading:count(1)");
    await click(".o-mail-Message .o-mail-Attachment-unlink");
    await expect.waitForSteps(["attachment_delete"]);
    await waitForNone(".o-mail-Message");
    expect.verifySteps([]);
});

test("leaving the page does not post messages waiting for their cloud upload", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patch(session, { cloud_storage_min_file_size: 0, cloud_storage_unsupported_models: [] });
    onRpcAfter("/mail/attachment/upload", async (response) => ({
        ...(await response),
        upload_info: { method: "PUT", url: "/cloud_storage/upload", response_status: 201 },
    }));
    onRpc("/cloud_storage/upload", () => {
        expect.step("cloud_upload");
        return new Promise(() => {}); // simulates a cloud upload that never completes
    });
    onRpcBefore("/mail/attachment/delete", () => expect.step("attachment_delete"));
    onRpcBefore("/mail/message/post", () => expect.step("message_post"));
    patch(XMLHttpRequest.prototype, {
        abort() {
            super.abort();
            this.onabort?.(); // notified by browsers, unlike the mocked request
        },
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer input[type=file]:count(1)");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await insertTextInComposer(".o-mail-Composer", "Dummy Message");
    await editInput(document.body, ".o-mail-Composer input[type=file]", [file]);
    await expect.waitForSteps(["cloud_upload"]);
    await press("Enter");
    await waitFor(
        ".o-mail-Message:has(:text('Dummy Message')) .o-mail-AttachmentContainer.o-isUploading:count(1)"
    );
    await manuallyDispatchProgrammaticEvent(window, "pagehide");
    await expect.waitForSteps(["attachment_delete"]);
    await waitForNone(".o-mail-Message");
    expect.verifySteps([]);
});
