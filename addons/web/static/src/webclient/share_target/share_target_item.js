import { Component, useState } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { checkFileSize } from "@web/core/utils/files";
import { Record } from "@web/model/record";
import { Field } from "@web/views/fields/field";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class ShareTargetItem extends Component {
    static template = "web.ShareTargetItem";
    static name = null;
    static sequence = 10;
    static components = { Record, Field };
    static props = {
        files: { type: Array, element: File },
    };

    setup() {
        super.setup();
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.http = useService("http");
        this.notification = useService("notification");
        this.orm = useService("orm");

        this.env.setHook({
            save: async () => {
                await this.checkAndActiveIfNeededUserCompany();
                await this.process();
            },
        });
        this.state = useState(this.defaultState);
    }

    get defaultState() {
        return {
            currentCompany: {
                id: user.activeCompany.id,
                display_name: user.activeCompany.name,
            },
        };
    }

    /**
     * @return {File[]}
     */
    getFiles() {
        return this.props.files.filter((file) => this.isAllowedUploadFile(file));
    }

    /**
     * @param {File} file
     */
    isAllowedUploadFile(file) {
        return checkFileSize(file.size, this.notification);
    }

    async checkAndActiveIfNeededUserCompany() {
        const companyId = this.currentCompany.id;
        const activeCompanyIds = user.activeCompanies.map((c) => c.id);
        if (!activeCompanyIds.includes(companyId)) {
            activeCompanyIds.push(companyId);
            await user.activateCompanies(activeCompanyIds, { reload: false });
        }
    }

    get allowedCompanies() {
        return user.allowedCompanies;
    }

    get currentCompany() {
        return this.state.currentCompany;
    }

    get hasMultiCompanies() {
        return this.allowedCompanies.length > 1;
    }

    async process() {
        const attachments = await this.uploadAttachments();
        const resId = await this.createRecordWithFile(attachments);
        await this.openCreatedRecord(resId);
    }

    /**
     * @return {String}
     */
    get name() {
        return this.constructor.name;
    }

    onCompanyChange(company) {
        this.state.currentCompany = company;
    }

    get multiCompaniesRecordProps() {
        return {
            mode: "readonly",
            values: { company: this.currentCompany },
            fieldNames: ["company"],
            fields: {
                company: { name: "company", type: "many2one", relation: "res.company" },
            },
            hooks: {
                onRecordChanged: (record) => {
                    this.onCompanyChange(record.data.company);
                },
            },
        };
    }

    get context() {
        return {
            ...user.context,
            allowed_company_ids: [this.currentCompany.id],
        };
    }

    /**
     * @return { String }
     */
    get modelName() {
        throw new Error("You should implement this !");
    }

    /**
     *
     * @param attachments {{ id: Number, filename: String }[]} the ir_attachment record
     * @return {Promise<?Number>} the res_id of the created record or null if the record wasn't saved
     */
    async createRecordWithFile(attachments) {
        const { filename } = attachments[0];
        const resId = await this._createRecord(filename, this.context);
        const attachmentIds = attachments.map((a) => a.id);
        await this.orm.write("ir.attachment", attachmentIds, {
            res_id: resId,
            res_model: this.modelName,
        });
        return resId;
    }

    async _createRecord(name, context) {
        try {
            const [resId] = await this.orm.call(this.modelName, "name_create", [name], {
                context,
            });
            return resId;
        } catch {
            // fallback on form view dialog when name_create fails
            return new Promise((resolve) => {
                this.dialog.add(FormViewDialog, {
                    canExpand: false,
                    close: resolve,
                    context: {
                        ...context,
                        default_name: name,
                    },
                    title: name,
                    resModel: this.modelName,
                    onRecordSaved: ({ resId }) => resolve(resId),
                });
            });
        }
    }

    async uploadAttachments() {
        const params = {
            csrf_token: odoo.csrf_token,
            ufile: this.getFiles(),
            model: this.modelName,
            id: 0,
        };
        const attachments = await this.http.post("/web/binary/upload_attachment", params);
        if (attachments.error) {
            throw new Error(attachments.error);
        }
        return attachments;
    }

    async openCreatedRecord(resId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: this.modelName,
            res_id: resId,
            views: [[false, "form"]],
            context: this.context,
        });
    }
}
