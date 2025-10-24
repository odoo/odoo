import { expect, test, runAllTimers } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { queryAllTexts } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
    webModels,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { onMounted, xml } from "@odoo/owl";
import { ShareTargetItem } from "@web/webclient/share_target/share_target_item";
import { WebClient } from "@web/webclient/webclient";
import { shareTargetService } from "@web/webclient/share_target/share_target_service";
import { ShareTargetDialog } from "@web/webclient/share_target/share_target_dialog";

const shareTargetRegistry = registry.category("share_target_items");

const pngFile = new File([new Uint8Array(1)], "text.png", { type: "image/png" });

test("Not sharing file should not trigger the share target dialog", async () => {
    patchWithCleanup(WebClient.prototype, {
        setup() {
            super.setup();
            onMounted(() => expect.step("web_client_mounted"));
        },
    });
    patchWithCleanup(shareTargetService, {
        _displayShareTarget() {
            expect.step("ask_to_display_dialog");
            return super._displayShareTarget(...arguments);
        },
        async _getShareTargetFiles() {
            expect.step("ask_for_available_files");
            return super._getShareTargetFiles();
        },
        start() {
            expect.step("start_service_share_target");
            return super.start(...arguments);
        },
    });
    shareTargetRegistry.add("fake_share_target", ShareTargetItem);
    await mountWithCleanup(WebClient);
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);
    expect.verifySteps([
        "start_service_share_target",
        "ask_for_available_files",
        "web_client_mounted",
        "ask_to_display_dialog",
    ]);
});

test("Sharing file should trigger the share target dialog", async () => {
    patchWithCleanup(shareTargetService, {
        _getShareTargetFiles: async () => [pngFile],
    });
    shareTargetRegistry.add("fake_share_target", ShareTargetItem);
    await mountWithCleanup(WebClient);
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect(".modal-footer .btn").toHaveCount(2);
    expect(".modal-footer .btn-primary").toHaveCount(1);
    expect(".modal-footer .btn-secondary").toHaveCount(1);
});

test("Sharing a pdf file should have a preview generated and have the file name", async () => {
    const pdfFile = new File([new Uint8Array(1)], "text.pdf", { type: "application/pdf" });
    patchWithCleanup(shareTargetService, {
        _getShareTargetFiles: async () => [pdfFile],
    });
    patchWithCleanup(ShareTargetDialog.prototype, {
        _generatePdfPreview: () => expect.step("generate_pdf_preview"),
    });
    shareTargetRegistry.add("fake_share_target", ShareTargetItem);
    await mountWithCleanup(WebClient);
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog img").toHaveCount(1);
    expect(".o_image").toHaveCount(1);
    expect(".o_image").toHaveAttribute("data-mimetype", "application/pdf");
    expect(".o_dialog div.text-truncate").toHaveText(pdfFile.name);
    expect.verifySteps(["generate_pdf_preview"]);
});

test("Sharing an image file should have a preview and a file name", async () => {
    patchWithCleanup(shareTargetService, {
        _getShareTargetFiles: async () => [pngFile],
    });
    patchWithCleanup(ShareTargetDialog.prototype, {
        _generatePdfPreview: () => expect.step("generate_pdf_preview"),
    });
    shareTargetRegistry.add("fake_share_target", ShareTargetItem);
    await mountWithCleanup(WebClient);
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog img").toHaveCount(1);
    expect(".o_image").toHaveCount(1);
    expect(".o_image").toHaveAttribute("data-mimetype", "image/png");
    expect(".o_dialog div.text-truncate").toHaveText(pngFile.name);
    expect.verifySteps([]);
});

test("ShareTargetItem Should respect the order", async () => {
    patchWithCleanup(shareTargetService, {
        _getShareTargetFiles: async () => [pngFile],
    });
    class ExpenseShareTargetItem extends ShareTargetItem {
        static name = "Expense";
        static sequence = 1;
    }
    class BillShareTargetItem extends ShareTargetItem {
        static name = "Bill";
        static sequence = 2;
    }
    class TimeOffShareTargetItem extends ShareTargetItem {
        static name = "Time Off";
        static sequence = 3;
    }
    class LeadShareTargetItem extends ShareTargetItem {
        static name = "Lead";
        static sequence = 4;
    }
    class TaskShareTargetItem extends ShareTargetItem {
        static name = "Task";
        static sequence = 5;
    }
    class ToDoShareTargetItem extends ShareTargetItem {
        static name = "To-Do";
        static sequence = 6;
    }
    class CustomShareTargetItem extends ShareTargetItem {
        static name = "CustomShareTarget";
    }
    class LolShareTargetItem extends ShareTargetItem {
        static name = "LolShareTarget";
    }
    // custom share target item first registered on the list
    shareTargetRegistry.add(LolShareTargetItem.name, LolShareTargetItem);
    shareTargetRegistry.add(CustomShareTargetItem.name, CustomShareTargetItem);
    shareTargetRegistry.add(TimeOffShareTargetItem.name, TimeOffShareTargetItem);
    shareTargetRegistry.add(LeadShareTargetItem.name, LeadShareTargetItem);
    shareTargetRegistry.add(TaskShareTargetItem.name, TaskShareTargetItem);
    shareTargetRegistry.add(ToDoShareTargetItem.name, ToDoShareTargetItem);
    shareTargetRegistry.add(ExpenseShareTargetItem.name, ExpenseShareTargetItem);
    shareTargetRegistry.add(BillShareTargetItem.name, BillShareTargetItem);

    await mountWithCleanup(WebClient);
    await animationFrame();
    expect(queryAllTexts(".o_dialog .modal-body .btn")).toEqual([
        "Expense",
        "Bill",
        "Time Off",
        "Lead",
        "Task",
        "To-Do",
        "LolShareTarget",
        "CustomShareTarget",
    ]);
});

test("Select an app should active the selected app button and render it's share target template", async () => {
    patchWithCleanup(shareTargetService, {
        _getShareTargetFiles: async () => [pngFile],
    });
    class CustomShareTargetItem1 extends ShareTargetItem {
        static name = "coucou";
        static template = xml`<p class="share_target_1" />`;
    }
    class CustomShareTargetItem2 extends ShareTargetItem {
        static name = "salut";
        static template = xml`<p class="share_target_2" />`;
    }
    shareTargetRegistry.add("fake_share_target_1", CustomShareTargetItem1);
    shareTargetRegistry.add("fake_share_target_2", CustomShareTargetItem2);
    await mountWithCleanup(WebClient);
    await animationFrame();
    expect(".modal-body button").toHaveCount(2);
    expect(".modal-body button:eq(0)").toHaveClass("active");
    expect(".modal-body button:eq(0)").toHaveText("coucou");
    expect(".modal-body button:eq(1)").not.toHaveClass("active");
    expect(".modal-body button:eq(1)").toHaveText("salut");
    expect(".share_target_1").toHaveCount(1);
    expect(".share_target_2").toHaveCount(0);

    await contains(".modal-body button:eq(1)").click();
    expect(".modal-body button:eq(0)").not.toHaveClass("active");
    expect(".modal-body button:eq(1)").toHaveClass("active");
    expect(".share_target_1").toHaveCount(0);
    expect(".share_target_2").toHaveCount(1);
});

test("Create button should call the check company and process method", async () => {
    patchWithCleanup(shareTargetService, {
        _getShareTargetFiles: async () => [pngFile],
    });
    class CustomShareTargetItem extends ShareTargetItem {
        static name = "hey";

        checkAndActiveIfNeededUserCompany() {
            expect.step("checkAndActiveIfNeededUserCompany");
            return super.checkAndActiveIfNeededUserCompany(...arguments);
        }
        process() {
            expect.step("process");
        }
    }
    shareTargetRegistry.add("fake_share_target", CustomShareTargetItem);
    await mountWithCleanup(WebClient);
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    await contains("footer .btn-primary").click();
    expect(".o_dialog").toHaveCount(0);
    expect.verifySteps(["checkAndActiveIfNeededUserCompany", "process"]);
});

test("res.company many2one should not display the company choice when having one company", async () => {
    patchWithCleanup(shareTargetService, {
        _getShareTargetFiles: async () => [pngFile],
    });
    shareTargetRegistry.add("fake_share_target", ShareTargetItem);
    await mountWithCleanup(WebClient);
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_many2one").toHaveCount(0);
});

test("res.company many2one should not display the company choice when having multi companies", async () => {
    serverState.companies = [
        {
            id: 1,
            display_name: "Company 1",
            name: "Company 1",
            sequence: 1,
            parent_id: false,
            child_ids: [],
        },
        {
            id: 2,
            display_name: "Company 2",
            name: "Company 2",
            sequence: 2,
            parent_id: false,
            child_ids: [],
        },
    ];
    patchWithCleanup(shareTargetService, {
        _getShareTargetFiles: async () => [pngFile],
    });
    shareTargetRegistry.add("fake_share_target", ShareTargetItem);
    await mountWithCleanup(WebClient);
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_many2one").toHaveCount(1);
});

test("res.company many2one should update the select value and use it on save", async () => {
    // Mock some companies
    serverState.companies = [
        {
            id: 1,
            display_name: "Company 1",
            name: "Company 1",
            sequence: 1,
            parent_id: false,
            child_ids: [],
        },
        {
            id: 2,
            display_name: "Company 2",
            name: "Company 2",
            sequence: 2,
            parent_id: false,
            child_ids: [],
        },
        {
            id: 3,
            display_name: "Company 3",
            name: "Company 3",
            sequence: 3,
            parent_id: false,
            child_ids: [],
        },
    ];
    const originalCompany = serverState.companies[0];
    const changedCompany = serverState.companies[1];
    webModels.ResCompany._views = {
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <div class="dropdown-item"><field name="display_name"/></div>
                    </t>
                </templates>
            </kanban>`,
    };
    defineModels([webModels.ResPartner, webModels.ResUsers, webModels.ResCompany]);

    // Mock the sharetarget files
    patchWithCleanup(shareTargetService, {
        _getShareTargetFiles: async () => [pngFile],
    });

    // mock upload rpc
    onRpc("/web/binary/upload_attachment", () => {
        expect.step("upload_attachments_server");
        return [{ id: 666, filename: pngFile.name }];
    });
    onRpc("/web/dataset/call_kw/ir.attachment/write", async (request) => {
        const { params } = await request.json();
        expect(params.args[0]).toEqual([666]);
        expect(params.args[1].res_model).toBe("res.users");
        return true;
    });

    class CustomShareTargetItem extends ShareTargetItem {
        static name = "hey";

        onCompanyChange(company) {
            expect.step(
                `onCompanyChange_from_${this.currentCompany.display_name}_to_${company.display_name}`
            );
            expect(this.context.allowed_company_ids).toEqual([originalCompany.id]);
            expect(this.currentCompany.id).toBe(originalCompany.id);
            expect(company.id).toBe(changedCompany.id);
            const result = super.onCompanyChange(...arguments);
            expect(this.currentCompany.id).toBe(changedCompany.id);
            expect(this.context.allowed_company_ids).toEqual([changedCompany.id]);
            return result;
        }
        get modelName() {
            return "res.users";
        }
        checkAndActiveIfNeededUserCompany() {
            expect.step("checkAndActiveIfNeededUserCompany");
            return super.checkAndActiveIfNeededUserCompany(...arguments);
        }
        process() {
            expect.step("process");
            expect(this.context.allowed_company_ids).toEqual([changedCompany.id]);
            return super.process(...arguments);
        }
        uploadAttachments() {
            expect.step(`upload_attachments`);
            return super.uploadAttachments(...arguments);
        }
        async createRecordWithFile(attachments) {
            expect.step(`create_record_${JSON.stringify(attachments)}`);
            return super.createRecordWithFile(...arguments);
        }
        async openCreatedRecord() {
            expect.step(`open_record`);
        }
    }
    shareTargetRegistry.add("fake_share_target", CustomShareTargetItem);

    await mountWithCleanup(WebClient);
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_many2one").toHaveCount(1);
    expect(".o_many2one input").toHaveValue(originalCompany.name);
    await animationFrame();
    await contains(".o_many2one input").click();
    await runAllTimers();
    expect(".dropdown-item:eq(0)").toHaveText(serverState.companies[0].name);
    expect(".dropdown-item:eq(1)").toHaveText(serverState.companies[1].name);
    expect(".dropdown-item:eq(2)").toHaveText(serverState.companies[2].name);
    await contains(".dropdown-item:eq(1)").click();
    expect(".o_many2one input").toHaveValue(changedCompany.name);
    await contains("footer .btn-primary").click();
    await runAllTimers();
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);
    expect.verifySteps([
        `onCompanyChange_from_${originalCompany.display_name}_to_${changedCompany.display_name}`,
        "checkAndActiveIfNeededUserCompany",
        "process",
        "upload_attachments",
        "upload_attachments_server",
        'create_record_[{"id":666,"filename":"text.png"}]',
        "open_record",
    ]);
});
