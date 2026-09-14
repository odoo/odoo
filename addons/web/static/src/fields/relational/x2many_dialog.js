// @ts-check
/** @odoo-module native */

import { Component, useComponent, useEffect, useEnv, useSubEnv } from "@odoo/owl";
import { useAction } from "@web/core/action_port";
import { makeContext } from "@web/core/context";
import { ModelEvent } from "@web/core/events";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { sharedComponents as shared } from "@web/core/shared_components";
import { _t } from "@web/core/translation";
import { createElement } from "@web/core/utils/dom/xml";
import {
    useBus,
    useChildRef,
    useOwnedDialogs,
    useService,
} from "@web/core/utils/hooks";
import { extractFieldsFromArchInfo } from "@web/model/relational_model";
import { Dialog } from "@web/ui/dialog";

const views = registry.category("views");
export class X2ManyFieldDialog extends Component {
    static template = "web.X2ManyFieldDialog";
    static get components() {
        return {
            Dialog,
            FormRenderer: views.get("form").Renderer,
            ViewButton: shared.get("ViewButton"),
        };
    }
    static props = {
        archInfo: Object,
        close: Function,
        record: Object,
        addNew: Function,
        save: Function,
        title: String,
        newRecordTitle: { type: String, optional: true },
        delete: { optional: true },
        deleteButtonLabel: { optional: true },
        config: Object,
        controls: { type: Array, optional: true },
    };
    static defaultProps = {
        controls: [],
    };
    /** @type {import("@web/core/action_port").ActionPort} */
    actionService;

    setup() {
        this.actionService = useAction();
        this.archInfo = this.props.archInfo;
        this.record = this.props.record;
        this.title = this.props.title;
        this.contentClass = shared.get("computeViewClassName")(
            "form",
            this.archInfo.xmlDoc,
        );
        useSubEnv({ config: this.props.config });
        this.env.dialogData.dismiss = () => this.discard();

        useBus(this.record.model.bus, ModelEvent.UPDATE, () => this.render());

        this.modalRef = useChildRef();

        const reload = () => this.record.load();

        shared.get("useViewButtons")(/** @type {any} */ (this.modalRef), {
            reload,
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
        });

        this._computePermissions();

        if (this.archInfo.xmlDoc.querySelector("footer:not(field footer)")) {
            this.archInfo = {
                ...this.archInfo,
                xmlDoc: this.archInfo.xmlDoc.cloneNode(true),
            };
            this.footerArchInfo = { ...this.archInfo };
            this.footerArchInfo.xmlDoc = createElement("t");
            this.footerArchInfo.xmlDoc.append(
                ...this.archInfo.xmlDoc.querySelectorAll("footer:not(field footer)"),
            );
            this.footerArchInfo.arch = this.footerArchInfo.xmlDoc.outerHTML;
            this.archInfo.arch = this.archInfo.xmlDoc.outerHTML;
        }

        const { autofocusFieldIds, disableAutofocus } = this.archInfo;
        if (!disableAutofocus) {
            useEffect(
                (isInEdition) => {
                    let elementToFocus;
                    if (isInEdition) {
                        for (const id of autofocusFieldIds) {
                            elementToFocus = /** @type {any} */ (
                                this.modalRef
                            ).el.querySelector(`#${id}`);
                            if (elementToFocus) {
                                break;
                            }
                        }
                        elementToFocus =
                            elementToFocus ||
                            /** @type {any} */ (this.modalRef).el.querySelector(
                                ".o_field_widget input",
                            );
                    } else {
                        elementToFocus = /** @type {any} */ (
                            this.modalRef
                        ).el.querySelector("button.btn-primary");
                    }
                    if (elementToFocus) {
                        elementToFocus.focus();
                    } else {
                        /** @type {any} */ (this.modalRef).el.focus();
                    }
                },
                () => [this.record.isInEdition],
            );
        }
        shared.get("useFormViewInDialog")();
    }

    _computePermissions() {
        this.readonly = Boolean(this.record.resId && !this.archInfo.activeActions.edit);
        this.canCreate = !this.record.resId;
    }

    /** @returns {Object} */
    get dialogProps() {
        const props = {
            title: this.title,
            withBodyPadding: false,
            modalRef: this.modalRef,
            contentClass: this.contentClass,
        };
        if (!this.record.isNew) {
            props.onExpand = async () => {
                await this.save({ saveAndNew: false });
                this.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: this.props.record.resModel,
                    res_id: this.props.record.resId,
                    views: [[false, "form"]],
                });
            };
        }
        return props;
    }

    /** @returns {boolean} */
    get displayDeleteButton() {
        const deleteControl = this.props.controls.find(
            (control) => control.type === "delete",
        );
        return (
            !deleteControl ||
            !evaluateBooleanExpr(deleteControl.invisible, this.record.evalContext)
        );
    }

    /** @param {{ special?: string }} clickParams */
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.special !== "cancel") {
            return this.record.save();
        }
    }

    async discard() {
        if (this.record.isInEdition) {
            await this.record.discard();
        }
        this.props.close();
    }

    /**
     * @param {{ saveAndNew: boolean }} params
     * @returns {Promise<boolean>}
     */
    save({ saveAndNew }) {
        return shared.get("executeButtonCallback")(
            /** @type {any} */ (this.modalRef).el,
            async () => {
                if (
                    await this.record.checkValidity({
                        displayNotification: true,
                    })
                ) {
                    await this.props.save(this.record);
                    if (saveAndNew) {
                        await this.record.switchMode("readonly");
                        this.record = await this.props.addNew();
                        this._computePermissions();
                    }
                } else {
                    return false;
                }
                if (!saveAndNew) {
                    this.props.close();
                }
                return true;
            },
        );
    }

    async remove() {
        await this.props.delete();
        this.props.close();
    }

    async saveAndNew() {
        const saved = await this.save({ saveAndNew: true });
        if (saved) {
            this.title = this.props.newRecordTitle || this.title;
            this.render(true);
        }
    }
}

/**
 * @param {Object} params
 * @param {Object} params.list
 * @param {Object} params.context
 * @param {Object} params.activeField
 * @param {Object} params.viewService
 * @param {Object} params.env
 * @returns {Promise<{archInfo: Object, fields: Object}>}
 */
async function getFormViewInfo({ list, context, activeField, viewService, env }) {
    let formArchInfo = activeField.views.form;
    let fields = activeField.fields;
    const comodel = list.resModel;
    if (!formArchInfo) {
        const {
            fields: formFields,
            relatedModels,
            views: loadedViews,
        } = await viewService.loadViews({
            context: makeContext([list.context, context]),
            resModel: comodel,
            views: [[false, "form"]],
        });
        const { ArchParser } = views.get("form");
        formArchInfo = new ArchParser().parse(
            loadedViews.form.ir,
            relatedModels,
            comodel,
        );
        fields = { ...list.fields, ...formFields };
    }

    await shared.get("loadSubViews")(
        formArchInfo.fieldNodes,
        fields,
        {},
        comodel,
        viewService,
        env.isSmall,
    );

    return { archInfo: formArchInfo, fields };
}

/**
 * @param {{ string: string }} activeField
 * @param {any} record
 * @param {string} [title]
 * @returns {{ title: string, newRecordTitle: string | undefined }}
 */
function getDialogTitles(activeField, record, title) {
    if (title) {
        return { title, newRecordTitle: undefined };
    }
    return {
        title: record
            ? _t("Open: %s", activeField.string)
            : _t("Create %s", activeField.string),
        newRecordTitle: _t("New: %s", activeField.string),
    };
}

/**
 * @param {{ isMany2Many: boolean, activeActions: any, readonly?: boolean }} params
 * @returns {"edit" | "readonly"}
 */
function getDialogMode({ isMany2Many, activeActions, readonly }) {
    if (isMany2Many) {
        return activeActions.write ? "edit" : "readonly";
    }
    return readonly || !activeActions.write ? "readonly" : "edit";
}

/**
 * @param {{ record: any, activeActions: any, viewMode: string }} params
 * @returns {{ deleteRecord: (() => any) | null | undefined, deleteButtonLabel: string | undefined }}
 */
function getDialogDeleteAction({ record, activeActions, viewMode }) {
    if (!record) {
        return { deleteRecord: undefined, deleteButtonLabel: undefined };
    }
    const { delete: canDelete, onDelete } = activeActions;
    return {
        deleteRecord:
            viewMode === "kanban" && canDelete ? () => onDelete(record) : null,
        deleteButtonLabel:
            activeActions.type === "one2many" ? _t("Delete") : _t("Remove"),
    };
}

/**
 * @typedef {{
 * activeField: any, activeActions: any, viewMode: string,
 * getList: () => any, updateRecord: Function, saveRecord: Function,
 * isMany2Many: boolean, viewService: any, env: any, component: any,
 * addDialog: Function,
 * }} X2ManyDialogContext
 */

/**
 * @param {X2ManyDialogContext} ctx
 * @param {{ record?: any, readonly?: boolean, context?: any, title?: string, controls?: any, onClose?: Function }} params
 */
async function openX2ManyRecord(
    ctx,
    { record, readonly, context, title, controls, onClose },
) {
    const { activeField, activeActions, viewMode, isMany2Many, getList } = ctx;
    const titles = getDialogTitles(activeField, record, title);
    const list = getList();
    let { archInfo, fields: _fields } = await getFormViewInfo({
        list,
        context,
        activeField,
        viewService: ctx.viewService,
        env: ctx.env,
    });
    if (!ctx.component.props.record.isInEdition) {
        archInfo = {
            ...archInfo,
            activeActions: { ...archInfo.activeActions, edit: false },
        };
    }
    const { activeFields, fields } = extractFieldsFromArchInfo(archInfo, _fields);

    const isExistingRecord = !!record;
    const params = {
        activeFields,
        fields,
        mode: getDialogMode({ isMany2Many, activeActions, readonly }),
    };
    const creationParams = {
        ...params,
        context: makeContext([list.context, context]),
        withoutParent: isMany2Many,
    };
    const { deleteRecord, deleteButtonLabel } = getDialogDeleteAction({
        record,
        activeActions,
        viewMode,
    });
    record = await list.extendRecord(record ? params : creationParams, record);

    ctx.addDialog(
        X2ManyFieldDialog,
        {
            config: ctx.env.config,
            archInfo,
            record,
            controls,
            addNew: () => getList().extendRecord(creationParams),
            save: (rec) =>
                isExistingRecord && rec.id === record.id
                    ? ctx.updateRecord(rec)
                    : ctx.saveRecord(rec),
            title: titles.title,
            newRecordTitle: titles.newRecordTitle,
            delete: deleteRecord,
            deleteButtonLabel,
        },
        {
            onClose: () => {
                list.editedRecord?.switchMode("readonly");
                onClose?.();
            },
        },
    );
}

export function useOpenX2ManyRecord({
    activeField,
    activeActions,
    getList,
    updateRecord,
    saveRecord,
    isMany2Many,
}) {
    /** @type {X2ManyDialogContext} */
    const ctx = {
        activeField,
        activeActions,
        viewMode: activeField.viewMode,
        getList,
        updateRecord,
        saveRecord,
        isMany2Many,
        viewService: useService("view"),
        env: useEnv(),
        component: useComponent(),
        addDialog: useOwnedDialogs(),
    };

    let recordIsOpen = false;
    return async (params) => {
        if (recordIsOpen) {
            return;
        }
        recordIsOpen = true;

        const onClose = params.onClose;
        params = {
            ...params,
            onClose: (...args) => {
                recordIsOpen = false;
                if (onClose) {
                    return onClose(...args);
                }
            },
        };

        try {
            return await openX2ManyRecord(ctx, params);
        } catch (e) {
            recordIsOpen = false;
            throw e;
        }
    };
}
