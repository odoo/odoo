import { expect, test } from "@odoo/hoot";
import {
    contains,
    getService,
    mockService,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { Deferred, animationFrame } from "@odoo/hoot-mock";
import { FileUploadProgressContainer } from "@web/core/file_upload/file_upload_progress_container";
import { FileUploadProgressRecord } from "@web/core/file_upload/file_upload_progress_record";
import { useService } from "@web/core/utils/hooks";

import { Component, xml } from "@odoo/owl";

class FileUploadProgressTestRecord extends FileUploadProgressRecord {
    static template = xml`
        <t t-set="progressTexts" t-value="getProgressTexts()"/>
        <div class="file_upload">
            <div class="file_upload_progress_text_left" t-esc="progressTexts.left"/>
            <div class="file_upload_progress_text_right" t-esc="progressTexts.right"/>
            <FileUploadProgressBar fileUpload="props.fileUpload"/>
        </div>
    `;
}
class Parent extends Component {
    static components = {
        FileUploadProgressContainer,
    };
    static template = xml`
        <div class="parent">
            <FileUploadProgressContainer fileUploads="fileUploadService.uploads" shouldDisplay="props.shouldDisplay" Component="FileUploadProgressTestRecord"/>
        </div>
    `;
    static props = ["*"];
    setup() {
        this.fileUploadService = useService("file_upload");
        this.FileUploadProgressTestRecord = FileUploadProgressTestRecord;
    }
}

onRpc("/test/", () => new Deferred());

test("can be rendered", async () => {
    await mountWithCleanup(Parent);
    expect(".parent").toHaveCount(1);
    expect(".file_upload").toHaveCount(0);
});

test("upload renders new component(s)", async () => {
    await mountWithCleanup(Parent);
    const fileUploadService = await getService("file_upload");
    fileUploadService.upload("/test/", []);
    await animationFrame();
    expect(".file_upload").toHaveCount(1);
    fileUploadService.upload("/test/", []);
    await animationFrame();
    expect(".file_upload").toHaveCount(2);
});

test("upload end removes component", async () => {
    await mountWithCleanup(Parent);

    const fileUploadService = await getService("file_upload");
    fileUploadService.upload("/test/", []);
    await animationFrame();
    fileUploadService.uploads[1].xhr.dispatchEvent(new Event("load"));
    await animationFrame();
    expect(".file_upload").toHaveCount(0);
});

test("upload error removes component", async () => {
    await mountWithCleanup(Parent);

    const fileUploadService = await getService("file_upload");
    fileUploadService.upload("/test/", []);
    await animationFrame();
    fileUploadService.uploads[1].xhr.dispatchEvent(new Event("error"));
    await animationFrame();
    expect(".file_upload").toHaveCount(0);
});

test("upload abort removes component", async () => {
    await mountWithCleanup(Parent);

    const fileUploadService = await getService("file_upload");
    fileUploadService.upload("/test/", []);
    await animationFrame();
    fileUploadService.uploads[1].xhr.dispatchEvent(new Event("abort"));
    await animationFrame();
    expect(".file_upload").toHaveCount(0);
});

test("upload can be aborted by clicking on cross", async () => {
    mockService("dialog", () => ({
        add() {
            fileUploadService.uploads[1].xhr.dispatchEvent(new Event("abort"));
        },
    }));
    await mountWithCleanup(Parent);
    const fileUploadService = await getService("file_upload");
    fileUploadService.upload("/test/", []);
    await animationFrame();
    await contains(".o-file-upload-progress-bar-abort", { visible: false }).click();
    await animationFrame();
    expect(".file_upload").toHaveCount(0);
});

test("upload updates on progress", async () => {
    await mountWithCleanup(Parent);

    const fileUploadService = await getService("file_upload");
    fileUploadService.upload("/test/", []);
    await animationFrame();

    const progressEvent = new Event("progress", { bubbles: true });
    progressEvent.loaded = 250000000;
    progressEvent.total = 500000000;
    fileUploadService.uploads[1].xhr.upload.dispatchEvent(progressEvent);
    await animationFrame();
    expect(".file_upload_progress_text_left").toHaveText("Uploading... (50%)");
    progressEvent.loaded = 350000000;
    fileUploadService.uploads[1].xhr.upload.dispatchEvent(progressEvent);
    await animationFrame();
    expect(".file_upload_progress_text_right").toHaveText("(350/500MB)");
});
