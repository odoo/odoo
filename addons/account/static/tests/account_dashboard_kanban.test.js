import { expect, test } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    defineModels,
    fields,
    mockUpload,
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
    mockUpload((route, params) => {
        uploads.push({ route, ...params });
        return { result: false };
    });
    await mountView({
        resModel: "account.journal",
        type: "kanban",
        arch: `
            <kanban js_class="account_dashboard_kanban">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <button type="upload" name="create_document_from_attachment" string="Upload"/>
                    </t>
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
    expect(".o-Dropzone").toHaveCount(1);
    expect(".o-Dropzone").toHaveText(/Bank/);

    queryOne(".o-Dropzone").dispatchEvent(
        dragEvent("drop", [new File(["x"], "a.pdf", { type: "application/pdf" })])
    );
    await animationFrame();
    await animationFrame();
    expect(uploads).toHaveLength(1);
    expect(uploads[0].route).toBe(
        "/web/dataset/call_upload/account.journal/create_document_from_attachment"
    );
    expect(uploads[0].res_ids).toBe("[7]");
});
