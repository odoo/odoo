import { browser } from "@web/core/browser/browser";
import {
    contains,
    defineModels,
    getService,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { inputFiles } from "@web/../tests/utils";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { waitFor, waitForNone, setInputFiles } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import {
    DocumentsModels,
    getBasicPermissionPanelData,
    getDocumentsTestServerData,
} from "./helpers/data";
import { makeDocumentsMockEnv } from "./helpers/model";
import { basicDocumentsKanbanArch, mountDocumentsKanbanView } from "./helpers/views/kanban";
import { getEnrichedSearchArch } from "./helpers/views/search";
import { WebClient } from "@web/webclient/webclient";

describe.current.tags("desktop");

defineModels({
    ...webModels,
    ...mailModels,
    ...DocumentsModels,
});

test("Open share with view user_permission", async function () {
    onRpc("/documents/touch/accessTokenFolder1", () => true);
    const serverData = getDocumentsTestServerData();
    const { id: folder1Id, name: folder1Name } = serverData.models["documents.document"].records[0];
    patchWithCleanup(browser.navigator.clipboard, {
        writeText: async (url) => {
            expect.step("Document url copied");
            expect(url).toBe("https://localhost:8069/odoo/documents/accessTokenFolder1");
        },
    });
    await makeDocumentsMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "permission_panel_data") {
                expect(args.args[0]).toEqual(folder1Id);
                expect.step("permission_panel_data");
                return getBasicPermissionPanelData({
                    access_url: "https://localhost:8069/odoo/documents/accessTokenFolder1",
                });
            }
            if (args.method === "can_upload_traceback") {
                return false;
            }
        },
    });
    await mountDocumentsKanbanView();
    await contains(`.o_kanban_record:contains(${folder1Name}) .o_record_selector`).click({
        ctrlKey: true,
    });
    await contains("button:contains(Share)").click();

    await contains(".o_clipboard_button", { timeout: 1500 }).click();
    expect.verifySteps(["permission_panel_data", "Document url copied"]);
});

test("Colorless-tags are also visible on cards", async function () {
    onRpc("/documents/touch/accessTokenFolder1", () => true);
    const serverData = getDocumentsTestServerData([
        {
            id: 2,
            folder_id: 1,
            name: "Testing tags",
            tag_ids: [1, 2],
        },
    ]);
    const { name: folder1Name } = serverData.models["documents.document"].records[0];
    const archWithTags = basicDocumentsKanbanArch.replace(
        '<field name="name"/>',
        '<field name="name"/>\n' +
        '<field name="tag_ids" class="d-block text-wrap" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>'
    );
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView({ arch: archWithTags });
    await contains(`.o_kanban_record:contains(${folder1Name})`).click();
    await animationFrame();
    expect(
        ".o_kanban_record:contains('Testing tags') div[name='tag_ids'] div .o_tag:nth-of-type(1)"
    ).toHaveText("Colorless");
    expect(
        ".o_kanban_record:contains('Testing tags') div[name='tag_ids'] div .o_tag:nth-of-type(2)"
    ).toHaveText("Colorful");
});

test("Download button availability", async function () {
    const serverData = getDocumentsTestServerData([
        {
            folder_id: 1,
            id: 2,
            name: "Request",
        },
        {
            attachment_id: 1,
            folder_id: 1,
            id: 3,
            name: "Binary",
        },
    ]);
    serverData.models["ir.attachment"] = {
        records: [{ id: 1, name: "binary" }],
    };
    const { name: folder1Name } = serverData.models["documents.document"].records[0];
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();
    await contains(`.o_kanban_record:contains(${folder1Name})`).click({ ctrlKey: true });
    // Folder should be downloadable
    await waitFor(".o_control_panel_actions:contains('Download')");

    await contains(`.o_kanban_record:contains(${folder1Name})`).click({ ctrlKey: true });
    // Request should not be downloadable
    await contains(".o_kanban_record:contains('Request')").click();
    await waitForNone(".o_control_panel_actions:contains('Download')");

    // Binary should be downloadable
    await contains(".o_kanban_record:contains('Binary')").click();
    await waitFor(".o_control_panel_actions:contains('Download')");
    // Multiple documents can be downloaded
    await contains(`.o_kanban_record:contains(${folder1Name})`).click({ ctrlKey: true });
    await waitFor(".o_control_panel_actions:contains('Download')");

    // Button should remain even if some records are not downloadable
    await contains(".o_kanban_record:contains('Request')").click({ ctrlKey: true });
    await waitFor(".o_control_panel_actions:contains('Download')");
});

test("Document Request Upload", async function () {
    mockService("file_upload", {
        upload: (route, files, params) => {
            if (route === "/documents/upload/accessToken") {
                expect.step("upload_done");
            }
        },
    });

    const serverData = getDocumentsTestServerData([
        {
            folder_id: 1,
            id: 2,
            name: "Test Request",
            access_token: "accessToken",
        },
    ]);

    const archWithRequest = basicDocumentsKanbanArch.replace(
        '<field name="name"/>',
        '<field name="name"/>\n' +
            '<t t-set="isRequest" t-value="record.type.raw_value === \'binary\' and !record.attachment_id.raw_value"/>\n' +
            '<input t-if="isRequest" type="file" class="o_hidden o_kanban_replace_document"/>\n'
    );
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView({ arch: archWithRequest });

    const file = new File(["hello world"], "text.txt", { type: "text/plain" });
    await inputFiles("input.o_kanban_replace_document", [file]);
    await animationFrame();
    expect.verifySteps(["upload_done"]);
});

test("Name in previewer is correct without attachment", async function () {
    const serverData = getDocumentsTestServerData([
        {
            id: 10,
            name: "Shin chan: The Spicy Kasukabe",
            type: "url",
            url: "https://www.youtube.com/watch?v=Qv_-R9kw5eg",
            mimetype: "text/html",
            folder_id: 1,
        },
        {
            id: 11,
            name: "Mom vs Dad |Shinchan",
            type: "url",
            url: "https://www.youtube.com/watch?v=sZeU-nrm8UA",
            mimetype: "text/html",
            folder_id: 1,
        },
    ]);

    const previewedAttachments = [];
    mockService("document.document", {
        setPreviewedDocument: (doc) => {
            if (doc && doc.attachment) {
                previewedAttachments.push({
                    id: doc.attachment.id,
                    name: doc.attachment.name,
                    url: doc.attachment.url,
                    documentId: doc.attachment.documentId,
                });
                expect.step(`preview_${doc.attachment.name}`);
            }
        },
        documentList: null,
    });

    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();

    await contains(".o_kanban_record:contains('Shin chan') [name='document_preview']").click();
    await waitFor(".o-FileViewer");

    const closeBtn = document.querySelector(".o-FileViewer [aria-label='Close']");
    closeBtn.click();
    await waitForNone(".o-FileViewer");

    await contains(".o_kanban_record:contains('Mom vs Dad') [name='document_preview']").click();
    await waitFor(".o-FileViewer");

    expect(previewedAttachments).toHaveLength(2);

    expect(previewedAttachments[0].id).toBe(-10);
    expect(previewedAttachments[0].name).toBe("Shin chan: The Spicy Kasukabe");

    expect(previewedAttachments[1].id).toBe(-11);
    expect(previewedAttachments[1].name).toBe("Mom vs Dad |Shinchan");

    expect.verifySteps(["preview_Shin chan: The Spicy Kasukabe", "preview_Mom vs Dad |Shinchan"]);
});

test("Split PDF button availability", async function () {
    const serverData = getDocumentsTestServerData([
        {
            attachment_id: 1,
            id: 2,
            name: "text_file.txt",
            user_permission: "edit",
            mimetype: "text/plain"
        },
        {
            attachment_id: 2,
            id: 3,
            name: "pdf1.pdf",
            user_permission: "view",
            mimetype: "application/pdf",
        },
        {
            attachment_id: 3,
            id: 4,
            name: "pdf2.pdf",
            user_permission: "edit",
            mimetype: "application/pdf",
        },
    ]);

    serverData.models["ir.attachment"] = {
        records: [
            { id: 1, name: "text_file.txt", mimetype: "text/plain" },
            { id: 2, name: "pdf1.pdf", mimetype: "application/pdf" },
            { id: 3, name: "pdf2.pdf", mimetype: "application/pdf",},
        ],
    };
    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView();

    // Non-PDF with edit permission
    await contains(".o_kanban_record:contains('text_file.txt') [name='document_preview']").click();
    await waitFor(".o-FileViewer");
    await waitForNone(".o-FileViewer-headerButton[title='Split PDF']");
    await waitForNone(".o_control_panel_actions .dropdown-menu .dropdown-item:contains('Split PDF')");

    // PDF with view permission
    await contains(".o_kanban_record:contains('pdf1.pdf') [name='document_preview']").click();
    await waitFor(".o-FileViewer");
    await waitForNone(".o-FileViewer-headerButton[title='Split PDF']");
    await waitForNone(".o_control_panel_actions .dropdown-menu .dropdown-item:contains('Split PDF')");

    // PDF with edit permission
    await contains(".o_kanban_record:contains('pdf2.pdf') [name='document_preview']").click();
    await waitFor(".o-FileViewer");
    await waitFor(".o-FileViewer-headerButton[title='Split PDF']");
    await waitFor(".o_control_panel_actions .dropdown-menu .dropdown-item:contains('Split PDF')");
});

test("Ensure previewer shows correct name after renaming a document", async function () {
    const serverData = getDocumentsTestServerData([
        {
            attachment_id: 1,
            id: 2,
            name: "text_file.txt",
            mimetype: "text/plain",
        },
    ]);

    DocumentsModels["DocumentsDocument"]._views = {
        kanban: basicDocumentsKanbanArch,
        search: getEnrichedSearchArch(),
        form: "<form><field name='name'/></form>",
    };

    serverData.models["ir.attachment"] = {
        records: [{ id: 1, name: "text_file.txt", mimetype: "text/plain" }],
    };

    await makeDocumentsMockEnv({ serverData });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "documents.document",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
    });

    await contains(".o_kanban_record:contains('text_file.txt')").click({ ctrlKey: true });
    await contains(".o_control_panel_actions button:contains('Action')").click();
    await contains(
        ".o_control_panel_actions .dropdown-menu .dropdown-item:contains('Rename')"
    ).click();
    await contains(".o_input").edit("test1.txt");
    await contains(".o_form_button_save:contains('Save')").click();
    expect(".o_kanban_record span:contains('test1.txt')").toHaveCount(1);
    await contains(".o_kanban_record:contains('test1.txt') [name='document_preview']").click();
    await waitFor(".o-FileViewer");
    expect(".o-FileViewer-header span:contains('test1.txt')").toHaveCount(1);
});

test("Uploading to 'All' from a bridge uploads to the bridge's default folder not 'My Drive'", async function () {
    onRpc("/documents/touch/<access_token>", () => ({}));
    mockService("file_upload", {
        upload: (route, files, params) => {
            if (route === "/documents/upload/accessTokenFolder1") {
                expect.step("upload_done");
            }
        },
    });

    const serverData = getDocumentsTestServerData();

    await makeDocumentsMockEnv({ serverData });
    await mountDocumentsKanbanView({ context: { searchpanel_default_folder_id: 1 } });

    await contains("span.o_search_panel_label_title:contains('All')").click();
    await contains("button.btn.btn-primary.dropdown-toggle").click();
    await contains("input.o_input_file.o_hidden", {
        visible: false,
    }).click();
    await animationFrame();
    await setInputFiles([new File(["fake_file"], "fake_file.tiff", { type: "text/plain" })]);
    await animationFrame();

    expect.verifySteps(["upload_done"]);
});
