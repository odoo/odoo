import { mergePeersSteps, setupMultiEditor } from "@html_editor/../tests/_helpers/collaboration";
import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { HtmlViewer } from "@html_editor/fields/html_viewer";
import { EmbeddedComponentPlugin } from "@html_editor/others/embedded_component_plugin";
import { fileEmbedding } from "@html_editor/others/embedded_components/backend/file/file";
import {
    ReadonlyEmbeddedFileComponent,
    readonlyFileEmbedding,
} from "@html_editor/others/embedded_components/core/file/readonly_file";
import { FilePlugin } from "@html_editor/others/embedded_components/plugins/file_plugin/file_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { onRpc, patchWithCleanup, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { expect, test } from "@odoo/hoot";
import { click, edit, press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { markup } from "@odoo/owl";

const config = {
    Plugins: [...MAIN_PLUGINS, EmbeddedComponentPlugin, FilePlugin],
    resources: {
        embeddedComponents: [fileEmbedding],
    },
};

const fileData = {
    id: 1,
    access_token: "4c22e31e-a125-4998-8e35-512f64c0fb7b",
    checksum: "a5d3f5eaa29fa01b32785d8d2a1e71e5cef0d2e",
    extension: "txt",
    filename: "Blah.txt",
    mimetype: "text/plain",
    name: "Blah.txt",
};

// download file route
onRpc("/web/content/1", async (request) => {
    expect(request.url).toBe(
        `https://www.hoot.test/web/content/1?access_token=${fileData.access_token}&filename=${fileData.name}&unique=${fileData.checksum}&download=true`,
    );
    expect.step("download file");
    return;
});

test("Insert an embedded file", async () => {
    // access token route
    onRpc("/web/dataset/call_kw/ir.attachment/generate_access_token", () => {
        return [fileData.access_token];
    });
    // media dialog route
    onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => {
        return [fileData];
    });

    const { editor } = await setupEditor("<p>a[]bc</p>", {
        config,
    });
    await insertText(editor, "/file");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);
    await press("Enter");
    await animationFrame();
    await click(".o_we_attachment_highlight");
    await animationFrame();
    expect("[data-embedded='file']").toHaveCount(1);
    // check filename prop
    expect(".o_file_name").toHaveText(fileData.filename);
    // check extension prop
    expect("[data-embedded='file'] .text-uppercase.small").toHaveText(
        fileData.extension.toUpperCase(),
    );
    // check mimetype prop
    expect(".o_file_image .o_image").toHaveAttribute("data-mimetype", fileData.mimetype);
    // user should see the rename file button
    expect(".o_embedded_file_name_container .fa-pencil").toHaveCount(1);
    // clicking on the icon should open the file viewer
    await click(".o_file_image .o_image");
    await animationFrame();
    expect(".o-FileViewer-view.o-isText").toHaveCount(1);
    // check access_token, name and checksum props
    expect(".o-FileViewer-view").toHaveAttribute(
        "data-src",
        `https://www.hoot.test/web/content/1?access_token=${fileData.access_token}&filename=${fileData.name}&unique=${fileData.checksum}`,
    );
    await press("esc");
    // check download params
    await click("button[name='download']");
    expect.verifySteps(["download file"]);
});

test("Embedded file url", async () => {
    patchWithCleanup(fileData, {
        checksum: false,
        extension: "jpg",
        filename: "myImage.jpg",
        mimetype: "image/jpeg",
        name: "myImage.jpg",
        type: "url",
        url: "https://www.hoot.test/myImage.jpg",
    });
    // download route
    onRpc("/myImage.jpg", async (request) => {
        expect(request.url).toBe(
            `${fileData.url}?access_token=${fileData.access_token}&filename=${fileData.name}&download=true`,
        );
        expect.step("download file");
        return;
    });

    await setupEditor(
        `<p>a[]bc</p><div data-embedded="file" data-embedded-props='${JSON.stringify({ fileData })}'></div>`,
        { config },
    );
    await animationFrame();
    expect("[data-embedded='file']").toHaveCount(1);
    // check name prop
    expect(".o_file_name").toHaveText(fileData.filename);
    // check extension prop
    expect("[data-embedded='file'] .text-uppercase.small").toHaveText(
        fileData.extension.toUpperCase(),
    );
    // check mimetype prop
    expect(".o_file_image .o_image").toHaveAttribute("data-mimetype", fileData.mimetype);
    // clicking on the icon should open the file viewer
    await click(".o_file_image .o_image");
    await animationFrame();
    expect(".o-FileViewer-view.o-FileViewer-viewImage").toHaveCount(1);
    // check access_token, filename and checksum props
    expect(".o-FileViewer-view").toHaveAttribute(
        "data-src",
        `${fileData.url}?access_token=${fileData.access_token}&filename=${fileData.name}`,
    );
    await press("esc");
    // check download params
    await click("button[name='download']");
    expect.verifySteps(["download file"]);
});

test("Rename a file in collaborative", async () => {
    patchWithCleanup(ReadonlyEmbeddedFileComponent, { props: ["*"] });
    const peerInfos = await setupMultiEditor({
        peerIds: ["c1", "c2"],
        contentBefore: `<p>[c1}{c1][c2}{c2]</p><div data-embedded='file' data-embedded-props='${JSON.stringify({ fileData })}'></div>`,
        ...config,
    });

    const e1 = peerInfos.c1.editor;
    const e2 = peerInfos.c2.editor;
    await animationFrame();
    expect(e1.editable.querySelector(".o_file_name")).toHaveText("Blah.txt");
    expect(e2.editable.querySelector(".o_file_name")).toHaveText("Blah.txt");
    click(e1.editable.querySelector("input[placeholder='Blah.txt']"));
    await animationFrame();
    edit("Zboing.txt", { confirm: "blur" });
    await animationFrame();
    e1.dispatch("ADD_STEP");
    mergePeersSteps(peerInfos);
    await animationFrame();
    expect(e1.editable.querySelector(".o_file_name")).toHaveText("Zboing.txt");
    expect(e2.editable.querySelector(".o_file_name")).toHaveText("Zboing.txt");
    // patch fileData so that check of download url params in onRpc checks for the new file name
    patchWithCleanup(fileData, { name: "Zboing.txt" });
    await click(e1.editable.querySelector("button[name='download']"));
    await click(e2.editable.querySelector("button[name='download']"));
    expect.verifySteps(["download file", "download file"]);
});

test("Embedded file in html viewer", async () => {
    await mountWithCleanup(HtmlViewer, {
        props: {
            config: {
                value: markup(
                    `<div data-embedded="file" data-embedded-props='${JSON.stringify({ fileData })}'/>`,
                ),
                embeddedComponents: [readonlyFileEmbedding],
            },
        },
    });
    expect("[data-embedded='file']").toHaveCount(1);
    // check filename prop
    expect(".o_file_name").toHaveText(fileData.filename);
    // check extension prop
    expect("[data-embedded='file'] .text-uppercase.small").toHaveText(
        fileData.extension.toUpperCase(),
    );
    // check mimetype prop
    expect(".o_file_image .o_image").toHaveAttribute("data-mimetype", fileData.mimetype);
    // user should not see the rename file button
    expect(".o_embedded_file_name_container .fa-pencil").toHaveCount(0);
    // clicking on the icon should open the file viewer
    await click(".o_file_image .o_image");
    await animationFrame();
    expect(".o-FileViewer-view.o-isText").toHaveCount(1);
    // check access_token, name and checksum props
    expect(".o-FileViewer-view").toHaveAttribute(
        "data-src",
        `https://www.hoot.test/web/content/1?access_token=${fileData.access_token}&filename=${fileData.name}&unique=${fileData.checksum}`,
    );
    await press("esc");
    // check download params
    await click("button[name='download']");
    expect.verifySteps(["download file"]);
});
