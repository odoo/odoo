/** @odoo-module native */
import { AccountReturnCheckKanbanRecord } from "@account/components/account_return/views/account_return_check_kanban_record";
import { WebChatter } from "@mail/chatter/web/web_chatter";
import { onWillDestroy, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    extractFieldsFromArchInfo,
    getFieldsSpec,
    RelationalModel,
} from "@web/model/relational_model";
import { KanbanRenderer } from "@web/views/kanban";
import { kanbanGroupKey } from "@web/views/view_utils";

import { AccountReturnKanbanRecord } from "./account_return_kanban_record.js";

const viewRegistry = registry.category("views");

export class AccountReturnCheckKanbanRenderer extends KanbanRenderer {
    static template = "account.account_return_check_kanban_renderer";

    static components = {
        ...KanbanRenderer.components,
        AccountReturnCheckKanbanRecord,
        AccountReturnKanbanRecord,
        Chatter: WebChatter,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.viewService = useService("view");
        const context = this.props.list.context;
        this.destroyed = false;
        this.originalListLoad = this.props.list.model.load.bind(this.props.list.model);

        onWillDestroy(async () => {
            this.destroyed = true;
        });

        if (context.active_model === "account.return") {
            this.currentReturnId = context.active_id;
            onWillStart(() => this._loadReturnRecord(context));
        }
    }

    async _loadReturnRecord(context) {
        const extractedFields = await this._loadReturnArchInfo(context);
        const accountReturnId = this.currentReturnId;
        if (!accountReturnId) {
            return;
        }
        this.specification = getFieldsSpec(
            extractedFields.activeFields,
            extractedFields.fields,
            context,
        );
        const returnData = await this._readReturn(accountReturnId);
        this.returnRecord = this._createReturnRecord(
            context,
            extractedFields,
            accountReturnId,
            returnData,
        );
        this.props.list.model.load = (params) =>
            this._reloadListAndReturn(params, accountReturnId);
        this._refreshChecks();
    }

    async _loadReturnArchInfo(context) {
        const { fields, relatedModels, views } = await this.viewService.loadViews({
            resModel: "account.return",
            context: context,
            views: [[context.account_return_view_id, "kanban"]],
        });
        const { ArchParser } = viewRegistry.get("kanban");
        this.returnArchInfo = new ArchParser().parse(
            views["kanban"].ir,
            relatedModels,
            "account.return",
        );
        return extractFieldsFromArchInfo(this.returnArchInfo, fields);
    }

    _readReturn(accountReturnId) {
        return this.orm.webRead("account.return", [accountReturnId], {
            specification: this.specification,
        });
    }

    _createReturnRecord(context, extractedFields, accountReturnId, returnData) {
        const modelParams = this.getModelParams(
            extractedFields.activeFields,
            extractedFields.fields,
        );
        const model = new RelationalModel(this.env, modelParams, { orm: this.orm });
        return new model.constructor.Record(
            model,
            {
                context: { ...context, in_checks_view: true },
                activeFields: extractedFields.activeFields,
                resModel: "account.return",
                fields: extractedFields.fields,
                resId: accountReturnId,
                resIds: [accountReturnId],
                isMonoRecord: true,
                mode: "readonly",
            },
            returnData[0],
            { manuallyAdded: !returnData.id },
        );
    }

    async _reloadListAndReturn(params, accountReturnId) {
        // Reload return card
        const result = await this.originalListLoad(params);
        if (this.destroyed) {
            return result;
        }
        const returnData = await this._readReturn(accountReturnId);
        if (this.destroyed) {
            return result;
        }
        this.returnRecord.setData(returnData[0]);

        // Reload chatter messages
        this.env.bus.trigger("MAIL:RELOAD-THREAD", {
            model: "account.return",
            id: accountReturnId,
        });

        return result;
    }

    _refreshChecks() {
        if (this.props.list.records.length === 0) {
            return;
        }
        const checkResults = this.orm.call("account.return", "refresh_checks", [
            this.currentReturnId,
        ]);
        checkResults.then(async () => {
            if (!this.destroyed) {
                await this.props.list.model.load();
            }
        });
    }

    getModelParams(activeFields, fields) {
        const modelConfig = {
            resModel: "account.return",
            fields,
            activeFields,
            openGroupsByDefault: true,
        };

        return {
            config: modelConfig,
            groupsLimit: Number.MAX_SAFE_INTEGER,
            limit: 1,
            countLimit: 1,
        };
    }

    get groups() {
        const { list } = this.props;
        if (!list.isGrouped) {
            return false;
        }
        return list.groups.map((group, index) => ({
            ...group,
            key: kanbanGroupKey(group, index),
        }));
    }

    async openRecord(record) {
        const recordId = record.resId;
        if (record.resModel === "account.return.check") {
            const result = await this.orm.call(record.resModel, "action_review", [
                recordId,
            ]);

            if (result) {
                this.action.doAction(result);
            }
        }
    }
}
