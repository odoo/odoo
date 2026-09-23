// @ts-check

import { expect, test } from "@odoo/hoot";
import { queryOne, setInputFiles, waitUntil } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    contains,
    mockService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { FileUploader } from "@web/core/file_upload/file_handler";
import { session } from "@web/session";

class Parent extends Component {
    static components = { FileUploader };
    static template = xml`
        <FileUploader
            onUploaded="this.props.onUploaded"
            onUploadComplete="this.props.onUploadComplete"
            multiUpload="this.props.multiUpload"
            checkSize="this.props.checkSize"
            allowedMIMETypes="this.props.allowedMIMETypes">
            <t t-set-slot="toggler">
                <button class="o_test_toggler">Upload</button>
            </t>
        </FileUploader>
    `;
    static props = ["*"];
}

test("FileUploader accepts only an exact allowed MIME and rejects empty type", async () => {
    const notifications = [];
    mockService("notification", {
        add: (message) => {
            notifications.push(message);
            return () => {};
        },
    });
    const uploaded = [];
    await mountWithCleanup(Parent, {
        props: {
            allowedMIMETypes: "application/pdf",
            onUploaded: (file) => uploaded.push(file.name),
        },
    });

    await contains(".o_test_toggler").click();
    await setInputFiles([new File(["%PDF-"], "ok.pdf", { type: "application/pdf" })]);
    await animationFrame();
    expect(uploaded).toEqual(["ok.pdf"]);
    expect(notifications).toHaveLength(0);

    await contains(".o_test_toggler").click();
    await setInputFiles([new File(["x"], "sub.pdf", { type: "pdf" })]);
    await animationFrame();
    expect(uploaded).toEqual(["ok.pdf"]);
    expect(notifications).toHaveLength(1);

    await contains(".o_test_toggler").click();
    await setInputFiles([new File(["x"], "unknown.bin", { type: "" })]);
    await animationFrame();
    expect(uploaded).toEqual(["ok.pdf"]);
    expect(notifications).toHaveLength(2);
});

test("FileUploader multi-upload continues past a too-large file and resets input", async () => {
    patchWithCleanup(session, { max_file_upload_size: 3 });
    mockService("notification", {
        add: () => () => {},
    });
    const uploaded = [];
    await mountWithCleanup(Parent, {
        props: {
            multiUpload: true,
            checkSize: true,
            onUploaded: (file) => uploaded.push(file.name),
        },
    });

    await contains(".o_test_toggler").click();
    await setInputFiles([
        new File(["ab"], "small_1.txt", { type: "text/plain" }),
        new File(["way-too-big"], "big.txt", { type: "text/plain" }),
        new File(["cd"], "small_2.txt", { type: "text/plain" }),
    ]);
    await waitUntil(() => uploaded.length === 2);

    expect(uploaded).toEqual(["small_1.txt", "small_2.txt"]);
    expect(/** @type {HTMLInputElement} */ (queryOne(".o_input_file")).value).toBe("");
});

test("FileUploader checkSize accepts a per-file predicate", async () => {
    patchWithCleanup(session, { max_file_upload_size: 3 });
    const notifications = [];
    mockService("notification", {
        add: (message) => {
            notifications.push(message);
            return () => {};
        },
    });
    const uploaded = [];
    await mountWithCleanup(Parent, {
        props: {
            multiUpload: true,
            checkSize: (file) => !file.name.startsWith("cloud"),
            onUploaded: (file) => uploaded.push(file.name),
        },
    });

    await contains(".o_test_toggler").click();
    await setInputFiles([
        new File(["cloud-bound-and-huge"], "cloud_big.txt", { type: "text/plain" }),
        new File(["way-too-big"], "local_big.txt", { type: "text/plain" }),
        new File(["ab"], "local_small.txt", { type: "text/plain" }),
    ]);
    await waitUntil(() => uploaded.length === 2);

    expect(uploaded).toEqual(["cloud_big.txt", "local_small.txt"]);
    expect(notifications).toHaveLength(1);
});
