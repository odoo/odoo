import { describe, test } from "@odoo/hoot";
import {
    assertSteps,
    click,
    contains,
    openView,
    registerArchs,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { inputFiles } from "@web/../tests/utils";
import { defineMrpModels } from "@mrp/../tests/mrp_test_helpers";
import { getService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { fileUploadService } from "@web/core/file_upload/file_upload_service";

describe.current.tags("desktop");
defineMrpModels();

const newArchs = {
    "product.document,false,kanban": `<kanban js_class="product_documents_kanban" create="false"><templates><t t-name="card">
                    <field name="name"/>
                </t></templates></kanban>`,
};

test("MRP documents kanban basic rendering", async () => {
    const pyEnv = await startServer();
    const irAttachment = pyEnv["ir.attachment"].create({
        mimetype: "image/png",
        name: "test.png",
    });
    pyEnv["product.document"].create([
        { name: "test1", ir_attachment_id: irAttachment, mimetype: "image/png" },
        { name: "test2" },
        { name: "test3" },
    ]);
    registerArchs(newArchs);
    await start();
    await openView({ res_model: "product.document", views: [[false, "kanban"]] });
    await contains("button[name='product_upload_document']");
    await contains(".o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)", { count: 3 });
    // check control panel buttons
    await contains(".o_cp_buttons .btn-primary", { text: "Upload" });
});

test("mrp: upload multiple files", async () => {
    const pyEnv = await startServer();
    const irAttachment = pyEnv["ir.attachment"].create({
        mimetype: "image/png",
        name: "test.png",
    });
    const text1 = new File(["hello, world"], "text1.txt", { type: "text/plain" });
    const text2 = new File(["hello, world"], "text2.txt", { type: "text/plain" });
    const text3 = new File(["hello, world"], "text3.txt", { type: "text/plain" });
    pyEnv["product.document"].create([
        { name: "test1", ir_attachment_id: irAttachment, mimetype: "image/png" },
        { name: "test2" },
        { name: "test3" },
    ]);

    registerArchs(newArchs);
    await start();
    await openView({ res_model: "product.document", views: [[false, "kanban"]] });

    getService("file_upload").bus.addEventListener("FILE_UPLOAD_ADDED", () => step("xhrSend"));
    await inputFiles(".o_control_panel_main_buttons .o_input_file", [text1]);
    assertSteps(["xhrSend"]);
    await inputFiles(".o_control_panel_main_buttons .o_input_file", [text2, text3]);
    assertSteps(["xhrSend"]);
});

test("mrp: click on image opens attachment viewer", async () => {
    const newArchs = {
        "product.document,false,kanban": `
                <kanban js_class="product_documents_kanban" create="false">
                    <templates>
                        <t t-name="card">
                            <div class="o_kanban_previewer" t-if="record.ir_attachment_id.raw_value">
                                <field name="ir_attachment_id" invisible="1"/>
                                <img t-attf-src="/web/image/#{record.ir_attachment_id.raw_value}" width="100" height="100" alt="Document" class="o_attachment_image"/>
                            </div>
                            <field name="name"/>
                            <field name="mimetype"/>
                        </t>
                    </templates>
                </kanban>`,
    };
    const pyEnv = await startServer();
    const irAttachment = pyEnv["ir.attachment"].create({
        mimetype: "image/png",
        name: "test.png",
    });
    pyEnv["product.document"].create([
        { name: "test1", ir_attachment_id: irAttachment, mimetype: "image/png" },
        { name: "test2" },
        { name: "test3" },
    ]);

    registerArchs(newArchs);
    await start();
    await openView({ res_model: "product.document", views: [[false, "kanban"]] });

    await click(".o_kanban_previewer");
    await contains(".o-FileViewer");
    await click(".o-FileViewer-headerButton .fa-times");
    await contains(".o-FileViewer", { count: 0 });
});

test("mrp: upload progress bars", async () => {
    const pyEnv = await startServer();
    const irAttachment = pyEnv["ir.attachment"].create({
        mimetype: "image/png",
        name: "test.png",
    });
    const text1 = new File(["hello, world"], "text1.txt", { type: "text/plain" });
    pyEnv["product.document"].create([
        { name: "test1", ir_attachment_id: irAttachment, mimetype: "image/png" },
        { name: "test2" },
        { name: "test3" },
    ]);

    registerArchs(newArchs);
    await start();
    await openView({ res_model: "product.document", views: [[false, "kanban"]] });

    let xhr;
    patchWithCleanup(fileUploadService, {
        createXhr() {
            xhr = super.createXhr(...arguments);
            xhr.send = () => {};
            return xhr;
        },
    });

    await inputFiles(".o_control_panel_main_buttons .o_input_file", [text1]);

    const progressEvent = new Event("progress", { bubbles: true });
    progressEvent.loaded = 250000000;
    progressEvent.total = 500000000;
    progressEvent.lengthComputable = true;
    xhr.upload.dispatchEvent(progressEvent);
    await contains(".o_file_upload_progress_text_left", { text: "Uploading... (50%)" });

    progressEvent.loaded = 350000000;
    xhr.upload.dispatchEvent(progressEvent);
    await contains(".o_file_upload_progress_text_right", { text: "(350/500MB)" });
});
