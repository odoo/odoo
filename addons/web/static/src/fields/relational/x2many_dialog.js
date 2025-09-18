// @ts-check

/** @module @web/fields/relational/x2many_dialog - Form dialog component for creating and editing x2many inline records */

import { Component, useComponent, useEffect, useEnv, useSubEnv } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { createElement, parseXML } from "@web/core/utils/dom/xml";
import {
    useBus,
    useChildRef,
    useOwnedDialogs,
    useService,
} from "@web/core/utils/hooks";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { Dialog } from "@web/ui/dialog/dialog";

const shared = registry.category("shared_components");
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
        delete: { optional: true },
        deleteButtonLabel: { optional: true },
        config: Object,
        controls: { type: Array, optional: true },
    };
    static defaultProps = {
        controls: [],
    };
    setup() {
        this.actionService = useService("action");
        this.archInfo = this.props.archInfo;
        this.record = this.props.record;
        this.title = this.props.title;
        this.contentClass = shared.get("computeViewClassName")(
            "form",
            this.archInfo.xmlDoc,
        );
        useSubEnv({ config: this.props.config });
        this.env.dialogData.dismiss = () => this.discard();

        useBus(this.record.model.bus, "update", () => this.render(true));

        this.modalRef = useChildRef();

        const reload = () => this.record.load();

        shared.get("useViewButtons")(/** @type {any} */ (this.modalRef), {
            reload,
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
        }); // maybe pass the model directly in props

        this.readonly = this.record.resId && !this.archInfo.activeActions.edit;
        this.canCreate = !this.record.resId;

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
            // to simplify
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

    /** @returns {Object} Props for the Dialog component */
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

    /** @returns {boolean} Whether the delete button should be visible */
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

    /** Discards unsaved changes and closes the dialog */
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

    /** Deletes the record and closes the dialog */
    async remove() {
        await this.props.delete();
        this.props.close();
    }

    /** Saves the current record and creates a new blank one in the dialog */
    async saveAndNew() {
        const saved = await this.save({ saveAndNew: true });
        if (saved) {
            if (this.title) {
                this.title = this.title.replace(_t("Open:"), _t("New:"));
            }
            this.render(true);
        }
    }
}

/**
 * Loads form view information for an x2many inline dialog.
 *
 * @param {Object} params
 * @param {Object} params.list - The x2many list
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
        const xmlDoc = parseXML(loadedViews.form.arch);
        formArchInfo = new ArchParser().parse(xmlDoc, relatedModels, comodel);
        // Fields that need to be defined are the ones in the form view, this is natural,
        // plus the ones that the list record has, that is, present in either the list arch
        // or the kanban arch of the one2many field
        fields = { ...list.fields, ...formFields }; // FIXME: update in place?
    }

    await shared.get("loadSubViews")(
        formArchInfo.fieldNodes,
        fields,
        {}, // context
        comodel,
        viewService,
        env.isSmall,
    );

    return { archInfo: formArchInfo, fields };
}

/**
 * Hook to open an x2many record in an inline dialog with form view.
 *
 * @param {Object} params
 * @param {Object} params.activeField
 * @param {Object} params.activeActions
 * @param {Function} params.getList
 * @param {Function} params.updateRecord
 * @param {Function} params.saveRecord
 * @param {boolean} params.isMany2Many
 * @returns {Function} openRecord
 */
export function useOpenX2ManyRecord({
    activeField, // TODO: this should be renamed (object with keys "viewMode", "views" and "string")
    activeActions,
    getList,
    updateRecord,
    saveRecord,
    isMany2Many,
}) {
    const viewService = useService("view");
    const env = useEnv();
    const component = useComponent();

    const addDialog = useOwnedDialogs();
    const viewMode = activeField.viewMode;

    async function openRecord({ record, readonly, context, title, controls, onClose }) {
        if (!title) {
            title = record
                ? _t("Open: %s", activeField.string)
                : _t("Create %s", activeField.string);
        }
        const list = getList();
        const { archInfo, fields: _fields } = await getFormViewInfo({
            list,
            context,
            activeField,
            viewService,
            env,
        });
        if (!component.props.record.isInEdition) {
            archInfo.activeActions.edit = false;
        }

        const { activeFields, fields } = extractFieldsFromArchInfo(archInfo, _fields);

        let deleteRecord;
        let deleteButtonLabel = undefined;
        const isDuplicate = !!record;

        const params = { activeFields, fields };
        if (isMany2Many) {
            params.mode = activeActions.write ? "edit" : "readonly";
        } else {
            params.mode = readonly || !activeActions.write ? "readonly" : "edit";
        }
        if (record) {
            const { delete: canDelete, onDelete } = activeActions;
            deleteRecord =
                viewMode === "kanban" && canDelete ? () => onDelete(record) : null;
            deleteButtonLabel =
                activeActions.type === "one2many" ? _t("Delete") : _t("Remove");
        } else {
            params.context = makeContext([list.context, context]);
            params.withoutParent = isMany2Many;
        }
        record = await list.extendRecord(params, record);

        const _onClose = () => {
            list.editedRecord?.switchMode("readonly");
            onClose?.();
        };

        addDialog(
            X2ManyFieldDialog,
            {
                config: env.config,
                archInfo,
                record,
                controls,
                addNew: () => getList().extendRecord(params),
                save: (rec) => {
                    if (isDuplicate && rec.id === record.id) {
                        return updateRecord(rec);
                    } else {
                        return saveRecord(rec);
                    }
                },
                title,
                delete: deleteRecord,
                deleteButtonLabel: deleteButtonLabel,
            },
            { onClose: _onClose },
        );
    }

    let recordIsOpen = false;
    return (params) => {
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
            return openRecord(params);
        } catch (e) {
            recordIsOpen = false;
            throw e;
        }
    };
}
