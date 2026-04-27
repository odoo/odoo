import { kanbanView } from "@web/views/kanban/kanban_view";
import { FieldStudio } from "@web_studio/client_action/view_editor/editors/components/field_studio";
import { WidgetStudio } from "@web_studio/client_action/view_editor/editors/components/widget_studio";
import { computeXpath } from "@web_studio/client_action/view_editor/editors/xml_utils";
import { ViewButtonStudio } from "@web_studio/client_action/view_editor/editors/components/view_button_studio";
import { StudioHook } from "@web_studio/client_action/view_editor/editors/components/studio_hook_component";
import { useService } from "@web/core/utils/hooks";

import { Component, toRaw, useEnv, useState, xml, onError } from "@odoo/owl";
import { KanbanEditorCompiler } from "./kanban_editor_compiler";

class FieldStudioKanbanRecord extends FieldStudio {
    isX2ManyEditable() {
        return false;
    }
}

const KanbanRecord = kanbanView.Renderer.components.KanbanRecord;

class KanbanEditorRecordMenu extends Component {
    static props = {
        slots: Object,
        studioXpath: String,
    };
    static template = xml`
        <div class="o_dropdown_kanban bg-transparent position-absolute end-0 top-0 o-web-studio-editor--element-clickable" t-att-studioXpath="props.studioXpath">
            <button class="btn o-no-caret rounded-0 pe-none" title="Dropdown menu">
                <span class="fa fa-ellipsis-v"/>
            </button>
        </div>
    `;
}

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

class SafeKanbanRecord extends KanbanRecord {
    static template = "web_studio.SafeKanbanRecord";
    setup() {
        super.setup();
        this.safe = useSafeKanban();
    }
    onGlobalClick() {
        // prevent click handling by the component
    }
}

class _KanbanEditorRecord extends KanbanRecord {
    static template = "web_studio.SafeKanbanRecord";
    static menuTemplate = "web_studio.SafeKanbanRecordMenu";
    static components = {
        ...KanbanRecord.components,
        Field: FieldStudioKanbanRecord,
        Widget: WidgetStudio,
        StudioHook,
        ViewButton: ViewButtonStudio,
        KanbanRecordMenu: KanbanEditorRecordMenu,
    };
    setup() {
        super.setup();
        this.viewEditorModel = useState(this.env.viewEditorModel);
        this.dialogService = useService("dialog");
        this.safe = useSafeKanban();
    }
    onGlobalClick(ev) {
        const el = ev.target.closest(".o-web-studio-editor--element-clickable");
        if (el) {
            this.env.config.onNodeClicked(el.getAttribute("studioxpath"));
        }
    }
    isFieldValueEmpty(value) {
        if (value === null) {
            return true;
        }
        if (Array.isArray(value)) {
            return !value.length;
        }
        return !value;
    }
    get dropdownXpath() {
        const compiledTemplateMenu = this.props.templates[this.constructor.KANBAN_MENU_ATTRIBUTE];
        return computeXpath(compiledTemplateMenu, "kanban");
    }
}

export class KanbanEditorRecord extends Component {
    static props = [...KanbanRecord.props];
    static template = xml`<t t-component="KanbanRecord" t-props="kanbanRecordProps" />`;

    get KanbanRecord() {
        if (this.env.viewEditorModel.mode !== "interactive") {
            return SafeKanbanRecord;
        } else {
            return _KanbanEditorRecord;
        }
    }
    get kanbanRecordProps() {
        const props = { ...this.props };
        if (this.env.viewEditorModel.mode === "interactive") {
            props.Compiler = KanbanEditorCompiler;
        }
        return props;
    }
}
