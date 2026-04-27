/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { kanbanView } from "@web/views/kanban/kanban_view";

import { KanbanEditorCompilerLegacy } from "@web_studio/client_action/view_editor/editors/kanban_legacy/kanban_editor_compiler_legacy";
import { FieldStudio } from "@web_studio/client_action/view_editor/editors/components/field_studio";
import { WidgetStudio } from "@web_studio/client_action/view_editor/editors/components/widget_studio";
import { ViewButtonStudio } from "@web_studio/client_action/view_editor/editors/components/view_button_studio";
import { StudioHook } from "@web_studio/client_action/view_editor/editors/components/studio_hook_component";
import { FieldSelectorDialog } from "@web_studio/client_action/view_editor/editors/components/field_selector_dialog";

import { computeXpath } from "@web_studio/client_action/view_editor/editors/xml_utils";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { Component, toRaw, useEnv, useState, xml, useEffect, useRef, onError } from "@odoo/owl";

class FieldStudioKanbanRecord extends FieldStudio {
    isX2ManyEditable() {
        return false;
    }
}

const OriginDropdown = kanbanView.Renderer.components.KanbanRecord.components.Dropdown;
class Dropdown extends OriginDropdown {
    static template = "web_studio.KanbanEditorRecord.Dropdown";
    static props = {
        ...OriginDropdown.props,
        studioXpath: { type: String, optional: 1 },
        hasCoverSetter: { type: Boolean, optional: 1 },
    };

    setup() {
        super.setup();
        const rootRef = useRef("root");
        useEffect(
            (rootEl) => {
                if (this.props.studioXpath) {
                    rootEl.classList.add("o-web-studio-editor--element-clickable");
                    rootEl.dataset.studioXpath = this.props.studioXpath;
                }

                if (this.props.hasCoverSetter) {
                    rootEl.dataset.hasCoverSetter = true;
                }
            },
            () => [rootRef.el]
        );
    }

    handleClick() {
        this.env.config.onNodeClicked(this.props.studioXpath);
    }
}

const KanbanRecord = kanbanView.Renderer.components.KanbanRecord;

function useSafeKanban() {
    const state = useState({ hasError: false });
    const viewEditorModel = toRaw(useEnv().viewEditorModel);
    onError((error) => {
        const hasError = state.hasError;
        if (hasError || viewEditorModel.isInEdition) {
            throw error;
        }
        state.hasError = true;
    });
    return state;
}

class SafeKanbanRecordLegacy extends KanbanRecord {
    static template = "web_studio.SafeKanbanRecordLegacy";
    setup() {
        super.setup();
        this.safe = useSafeKanban();
    }
}

class _KanbanEditorRecord extends KanbanRecord {
    static template = "web_studio.SafeKanbanRecordLegacy";
    static menuTemplate = "web_studio.SafeKanbanRecordLegacyMenu";
    static components = {
        ...KanbanRecord.components,
        Dropdown,
        Field: FieldStudioKanbanRecord,
        Widget: WidgetStudio,
        StudioHook,
        ViewButton: ViewButtonStudio,
    };
    setup() {
        super.setup();
        this.viewEditorModel = useState(this.env.viewEditorModel);
        if (this.constructor.LEGACY_KANBAN_MENU_ATTRIBUTE in this.props.templates) {
            const compiledTemplateMenu =
                this.props.templates[this.constructor.LEGACY_KANBAN_MENU_ATTRIBUTE];
            this.dropdownXpath = computeXpath(compiledTemplateMenu, "kanban");
            this.dropdownHasCoverSetter = Boolean(
                compiledTemplateMenu.querySelectorAll("a[data-type='set_cover']").length
            );
        }
        this.dialogService = useService("dialog");

        this.safe = useSafeKanban();
    }

    onGlobalClick() {}

    isFieldValueEmpty(value) {
        if (value === null) {
            return true;
        }
        if (Array.isArray(value)) {
            return !value.length;
        }
        return !value;
    }

    onAddTagsWidget({ xpath }) {
        const fields = [];
        for (const [fName, field] of Object.entries(this.props.record.fields)) {
            if (field.type === "many2many") {
                const _field = { ...field, name: fName };
                fields.push(_field);
            }
        }

        if (!fields.length) {
            this.dialogService.add(AlertDialog, {
                body: _t("You first need to create a many2many field in the form view."),
            });
            return;
        }

        this.dialogService.add(FieldSelectorDialog, {
            fields,
            onConfirm: (field) => {
                const operation = {
                    type: "add",
                    node: {
                        tag: "field",
                        attrs: { name: field },
                    },
                    target: this.env.viewEditorModel.getFullTarget(xpath),
                    position: "inside",
                };
                this.env.viewEditorModel.doOperation(operation);
            },
        });
    }

    onAddDropdown() {
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Do you want to add a dropdown with colors?"),
            confirm: () => {
                this.env.viewEditorModel.doOperation({
                    type: "kanban_dropdown",
                });
            },
        });
    }

    onAddPriority() {
        const fields = [];
        const activeFields = Object.keys(this.props.record.activeFields);
        for (const [fName, field] of Object.entries(this.props.record.fields)) {
            if (field.type === "selection" && !activeFields.includes(fName)) {
                const _field = { ...field, name: fName };
                fields.push(_field);
            }
        }
        this.dialogService.add(FieldSelectorDialog, {
            fields,
            showNew: true,
            onConfirm: (field) => {
                this.env.viewEditorModel.doOperation({
                    type: "kanban_priority",
                    field,
                });
            },
        });
    }

    onAddAvatar() {
        const fields = [];
        for (const [fName, field] of Object.entries(this.props.record.fields)) {
            if (
                field.type === "many2one" &&
                (field.relation === "res.partner" || field.relation === "res.users")
            ) {
                const _field = { ...field, name: fName };
                fields.push(_field);
            }
        }
        this.dialogService.add(FieldSelectorDialog, {
            fields,
            onConfirm: (field) => {
                this.env.viewEditorModel.doOperation({
                    type: "kanban_image",
                    field,
                });
            },
        });
    }
}

export class KanbanEditorRecordLegacy extends Component {
    static props = [...KanbanRecord.props];
    static template = xml`<t t-component="KanbanRecord" t-props="kanbanRecordProps" />`;

    get KanbanRecord() {
        if (this.env.viewEditorModel.mode !== "interactive") {
            return SafeKanbanRecordLegacy;
        } else {
            return _KanbanEditorRecord;
        }
    }
    get kanbanRecordProps() {
        const props = { ...this.props };
        if (this.env.viewEditorModel.mode === "interactive") {
            props.Compiler = KanbanEditorCompilerLegacy;
        }
        return props;
    }
}
