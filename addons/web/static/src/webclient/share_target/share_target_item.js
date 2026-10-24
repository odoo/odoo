import { Component, onWillDestroy, proxy, t, useProps } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { Record } from "@web/model/record";
import { Field } from "@web/views/fields/field";
import { uploadFiles } from "@web/views/view_button/upload_button";

export class ShareTargetItem extends Component {
    static template = "web.ShareTargetItem";
    static name = null;
    static sequence = 10;
    static components = { Record, Field };
    props = useProps({
        files: t.array(t.instanceOf(File)),
    });

    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");

        const shareTarget = useService("share_target");
        onWillDestroy(
            shareTarget.setHook("save", async () => {
                await this.checkAndActiveIfNeededUserCompany();
                await this.process();
            })
        );

        this.state = proxy(this.defaultState);
    }

    get defaultState() {
        return {
            currentCompany: {
                id: user.activeCompany.id,
                display_name: user.activeCompany.name,
            },
        };
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
        const action = await uploadFiles(this.env.services, {
            clickParams: { name: "action_create_from_uploads" },
            resModel: this.modelName,
            context: this.context,
            files: this.props.files,
        });
        if (action) {
            await this.action.doAction(action, { additionalContext: this.context });
        }
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
}
