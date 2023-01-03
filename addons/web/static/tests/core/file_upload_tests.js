/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { fileUploadService } from "@web/core/file_upload/file_upload_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { FileUploadProgressContainer } from "@web/core/file_upload/file_upload_progress_container";
import { FileUploadProgressRecord } from "@web/core/file_upload/file_upload_progress_record";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, mount, nextTick, patchWithCleanup } from "../helpers/utils";

import { Component, xml } from "@odoo/owl";
const serviceRegistry = registry.category("services");

class FileUploadProgressTestRecord extends FileUploadProgressRecord {}
FileUploadProgressTestRecord.template = xml`
    <t t-set="progressTexts" t-value="getProgressTexts()"/>
    <div class="file_upload">
        <div class="file_upload_progress_text_left" t-esc="progressTexts.left"/>
        <div class="file_upload_progress_text_right" t-esc="progressTexts.right"/>
        <FileUploadProgressBar fileUpload="props.fileUpload"/>
    </div>
`;
class Parent extends Component {
    setup() {
        this.fileUploadService = useService("file_upload");
        this.FileUploadProgressTestRecord = FileUploadProgressTestRecord;
    }
}
Parent.components = {
    FileUploadProgressContainer,
};
Parent.template = xml`
    <div class="parent">
        <FileUploadProgressContainer fileUploads="fileUploadService.uploads" shouldDisplay="props.shouldDisplay" Component="FileUploadProgressTestRecord"/>
    </div>
`;

let env;
let target;
let patchUpload;

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(async () => {
        serviceRegistry.add("file_upload", fileUploadService);
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("localization", makeFakeLocalizationService());
        patchUpload = (customSend) => {
            patchWithCleanup(fileUploadService, {
                createXhr() {
                    const xhr = new window.EventTarget();
                    Object.assign(xhr, {
                        upload: new window.EventTarget(),
                        open() {},
                        send(data) { customSend && customSend(data); },
                    });
                    return xhr;
                },
            });
        };
        target = getFixture();
    });

    QUnit.module("FileUploadProgressContainer");

    QUnit.test("can be rendered", async (assert) => {
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        assert.containsOnce(target, ".parent");
        assert.containsNone(target, ".file_upload");
    });

    QUnit.test("upload renders new component(s)", async (assert) => {
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        patchUpload();
        const fileUploadService = env.services.file_upload;
        fileUploadService.upload("/test/", []);
        await nextTick();
        assert.containsOnce(target, ".file_upload");
        fileUploadService.upload("/test/", []);
        await nextTick();
        assert.containsN(target, ".file_upload", 2);
    });

    QUnit.test("upload end removes component", async (assert) => {
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        patchUpload();
        const fileUploadService = env.services.file_upload;
        fileUploadService.upload("/test/", []);
        await nextTick();
        fileUploadService.uploads[1].xhr.dispatchEvent(new Event("load"));
        await nextTick();
        assert.containsNone(target, ".file_upload");
    });

    QUnit.test("upload error removes component", async (assert) => {
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        patchUpload();
        const fileUploadService = env.services.file_upload;
        fileUploadService.upload("/test/", []);
        await nextTick();
        fileUploadService.uploads[1].xhr.dispatchEvent(new Event("error"));
        await nextTick();
        assert.containsNone(target, ".file_upload");
    });

    QUnit.test("upload abort removes component", async (assert) => {
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        patchUpload();
        const fileUploadService = env.services.file_upload;
        fileUploadService.upload("/test/", []);
        await nextTick();
        fileUploadService.uploads[1].xhr.dispatchEvent(new Event("abort"));
        await nextTick();
        assert.containsNone(target, ".file_upload");
    });

    QUnit.test("upload can be aborted by clicking on cross", async (assert) => {
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        patchUpload();
        const fileUploadService = env.services.file_upload;
        fileUploadService.upload("/test/", []);
        await nextTick();
        patchWithCleanup(env.services.dialog, {
            add: () => {
                fileUploadService.uploads[1].xhr.dispatchEvent(new Event("abort"));
            },
        });
        await click(target, ".o-file-upload-progress-bar-abort", true);
        assert.containsNone(target, ".file_upload");
    });

    QUnit.test("upload updates on progress", async (assert) => {
        env = await makeTestEnv();
        await mount(Parent, target, { env });
        patchUpload();
        const fileUploadService = env.services.file_upload;
        fileUploadService.upload("/test/", []);
        await nextTick();

        const progressEvent = new Event("progress", { bubbles: true });
        progressEvent.loaded = 250000000;
        progressEvent.total = 500000000;
        fileUploadService.uploads[1].xhr.upload.dispatchEvent(progressEvent);
        await nextTick();
        assert.strictEqual(target.querySelector(".file_upload_progress_text_left").textContent, "Uploading... (50%)");
        progressEvent.loaded = 350000000;
        fileUploadService.uploads[1].xhr.upload.dispatchEvent(progressEvent);
        await nextTick();
        assert.strictEqual(target.querySelector(".file_upload_progress_text_right").textContent, "(350/500MB)");
    });
});
