import { expect, test } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { EventBus } from "@odoo/owl";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

import "@account/views/account_dashboard_kanban/account_dashboard_kanban_view";

class AccountJournal extends models.Model {
    _name = "account.journal";
    name = fields.Char();
    _records = [{ id: 7, name: "Bank" }];
}

defineMailModels();
defineModels([AccountJournal]);

test.tags("desktop");
test("dashboard card: dropping files calls create_document_from_attachment on the journal", async () => {
    onRpc("get_account_dashboard_kpis", () => []);
    const uploads = [];
    const bus = new EventBus();
    mockService("file_upload", {
        bus,
        uploads: {},
        async upload(route, files, { buildFormData }) {
            const formData = new FormData();
            buildFormData(formData);
            const upload = {
                id: uploads.length + 1,
                data: formData,
                state: "loaded",
                response: { result: false },
            };
            uploads.push({ route, formData });
            setTimeout(() => bus.trigger("FILE_UPLOAD_LOADED", { upload }));
            return upload;
        },
    });
    await mountView({
        resModel: "account.journal",
        type: "kanban",
        arch: `
            <kanban js_class="account_dashboard_kanban">
                <templates>
                    <t t-name="card"><field name="name"/></t>
                </templates>
            </kanban>`,
    });
    const dragEvent = (type, files = []) => {
        const ev = new Event(type, { bubbles: true, cancelable: true });
        Object.defineProperty(ev, "dataTransfer", { value: { types: ["Files"], files } });
        return ev;
    };
    queryOne(".o_kanban_record:contains(Bank)").dispatchEvent(dragEvent("dragenter"));
    await animationFrame();
    expect(".o-UploadDropzone").toHaveCount(1);
    expect(".o-UploadDropzone").toHaveText(/Bank/);

    queryOne(".o-UploadDropzone").dispatchEvent(
        dragEvent("drop", [new File(["x"], "a.pdf", { type: "application/pdf" })])
    );
    await animationFrame();
    expect(uploads).toHaveLength(1);
    expect(uploads[0].formData.get("method")).toBe("create_document_from_attachment");
    expect(uploads[0].formData.get("res_ids")).toBe("[7]");
});
