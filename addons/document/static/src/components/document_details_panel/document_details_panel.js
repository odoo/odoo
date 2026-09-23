/** @odoo-module native */
import { useComputed } from "@web/core/utils/computed";
import { humanSize } from "@web/core/utils/format/binary";
import { _t } from "@web/core/translation";
import { ModelSelector } from "@web/components/model_selector";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { CharField } from "@web/fields/basic/char/char_field";
import { Many2OneAvatarField } from "@web/fields/relational/many2one_avatar/many2one_avatar_field";
import { Many2OneField } from "@web/fields/relational/many2one";
import { SelectCreateDialog } from "@web/views/view_dialogs";

import { DocumentsDetailsMany2ManyTagsField } from "@document/views/fields/document_details_many2many_tags/document_details_many2many_tags_field";
import { DocumentsDetailsMany2OneField } from "@document/views/fields/document_details_many2one/document_details_many2one_field";
import { DocumentsTypeIcon } from "@document/views/fields/document_type_icon/document_type_icon";

import { Component, onWillUpdateProps, status, useState } from "@odoo/owl";

export class DocumentsDetailsPanel extends Component {
    static components = {
        CharField,
        DocumentsDetailsMany2ManyTagsField,
        DocumentsDetailsMany2OneField,
        DocumentsTypeIcon,
        Many2OneAvatarField,
        Many2OneField,
        ModelSelector,
    };
    static props = {
        record: { type: Object },
        nbViewItems: { type: Number, optional: true },
    };
    static template = "document.DocumentsDetailsPanel";

    setup() {
        this.action = useService("action");
        /** @type {import("@document/core/document_service").DocumentService} */
        this.documentService = useService("document.document");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.detailsRecord = useComputed(
            () => wrapAsDetailsPanelRecord(this.props.record),
            () => [this.props.record],
        );

        this.state = useState({
            resModel: this.props.record.data.res_model,
            resModelName: this.props.record.data.res_model_name || "",
            models: [],
        });
        this.documentService.getDetailsPanelResModels().then((models) => {
            // The panel may be gone by the time the RPC answers.
            if (status(this) !== "destroyed") {
                this.state.models = models;
            }
        });
        onWillUpdateProps((nextProps) => {
            this.state.resModel = nextProps.record.data.res_model;
            this.state.resModelName = nextProps.record.data.res_model_name || "";
        });
    }

    get record() {
        return this.detailsRecord();
    }

    async openLinkedRecord() {
        const { res_model, res_id } = this.record.data || {};
        if (!res_id?.resId || !res_model) {
            return;
        }
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_id: res_id.resId,
            res_model,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openAccessLog() {
        const action = await this.orm.call(
            "document.document",
            "action_view_access_log",
            [this.record.resId],
        );
        return this.action.doAction(action);
    }

    get canViewAccessLog() {
        return this.documentService.userIsDocumentManager && !!this.record.resId;
    }

    get userPermissionViewOnly() {
        return (
            !!this.record.data?.lock_uid ||
            this.record.data?.user_permission !== "edit" ||
            (!this.documentService.userIsDocumentManager &&
                this.record.data?.user_folder_id === "COMPANY")
        );
    }

    get fileSize() {
        const data = this.record.data;
        const isFolderTotal = this.props.record.isContainer;
        if (data.type === "folder" && !isFolderTotal) {
            return "";
        }
        const nBytes = data.file_size || 0;
        if (!nBytes) {
            return "";
        }
        return `${isFolderTotal ? "~" : ""}${humanSize(nBytes)}`;
    }

    get rootFolderPlaceholder() {
        return {
            MY: _t("My Drive"),
            COMPANY: _t("Company"),
            SHARED: _t("Shared with me"),
        }[this.props.record.data?.user_folder_id];
    }

    get activeCompanies() {
        return user.activeCompanies.map((c) => c.id);
    }

    async onModelSelected(value) {
        this.state.resModel = value.technical;
        this.state.resModelName = value.label || "";
        await this.record.update({ res_id: false, res_model: false }, { save: true });
        if (this.state.resModel) {
            this.dialog.add(
                SelectCreateDialog,
                {
                    title: _t("Select a Record To Link"),
                    noCreate: true,
                    multiSelect: false,
                    resModel: this.state.resModel,
                    onSelected: async (resIds) => {
                        if (resIds.length) {
                            await this.onResIdUpdate(resIds);
                        }
                    },
                },
                {
                    onClose: () => {
                        if (!this.record.data.res_id) {
                            this.onRecordReset();
                        }
                    },
                },
            );
        }
    }

    async onRecordReset() {
        await this.onModelSelected({ technical: false, label: false });
    }

    async onResIdUpdate(value) {
        if (this.state.resModel) {
            await this.record.update(
                { res_id: value[0], res_model: this.state.resModel },
                { save: true },
            );
        }
    }
}

/**
 * @param {Object} record
 * @returns {Object}
 */
function wrapAsDetailsPanelRecord(record) {
    return new Proxy(record, {
        get(target, prop, receiver) {
            return (
                prop === "isDetailsPanelRecord" || Reflect.get(target, prop, receiver)
            );
        },
    });
}
