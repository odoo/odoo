/** @odoo-module */
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanEditorRenderer } from "@web_studio/client_action/view_editor/editors/kanban/kanban_editor_renderer";
import { makeModelErrorResilient } from "@web_studio/client_action/view_editor/editors/utils";
import { KanbanEditorSidebar } from "./kanban_editor_sidebar/kanban_editor_sidebar";
import { getStudioNoFetchFields, useModelConfigFetchInvisible } from "../utils";

class EditorArchParser extends kanbanView.ArchParser {
    parse(arch, models, modelName) {
        const parsed = super.parse(...arguments);
        const noFetch = getStudioNoFetchFields(parsed.fieldNodes);
        parsed.fieldNodes = omit(parsed.fieldNodes, ...noFetch.fieldNodes);
        parsed.progressAttributes = false;
        return parsed;
    }
}
class OneRecordModel extends kanbanView.Model {
    async load() {
        this.progressAttributes = false;
        await super.load(...arguments);
        let list = this.root;
        let hasRecords;
        const isGrouped = list.isGrouped;
        if (!isGrouped) {
            hasRecords = list.records.length;
        } else {
            hasRecords = list.groups.some((g) => g.list.records.length);
        }
        if (!hasRecords) {
            if (isGrouped) {
                const commonConfig = {
                    resModel: list.config.resModel,
                    fields: list.config.fields,
                    activeFields: list.config.activeFields,
                    groupByFieldName: list.groupByField.name,
                    context: list.context,
                    list: {
                        resModel: list.config.resModel,
                        fields: list.config.fields,
                        activeFields: list.config.activeFields,
                        groupBy: [],
                        context: list.context,
                    },
                };

                const data = {
                    count: 0,
                    length: 0,
                    records: [],
                    __domain: [],
                    value: "fake",
                    displayName: "fake",
                    groups: [
                        {
                            display_name: false,
                            count: 0,
                        },
                    ],
                };

                list.config.groups.fake = commonConfig;

                const group = list._createGroupDatapoint(data);
                list.groups.push(group);
                list = group.list;
            }
            await list.addNewRecord();
        }
    }
}

class KanbanEditorController extends kanbanView.Controller {
    setup() {
        super.setup();
        useModelConfigFetchInvisible(this.model);
    }

    get modelParams() {
        const params = super.modelParams;
        params.groupsLimit = 1;
        return params;
    }
}

const kanbanEditor = {
    ...kanbanView,
    Controller: KanbanEditorController,
    ArchParser: EditorArchParser,
    Renderer: KanbanEditorRenderer,
    Model: OneRecordModel,
    Sidebar: KanbanEditorSidebar,
    props(genericProps, editor, config) {
        const props = kanbanView.props(genericProps, editor, config);
        props.defaultGroupBy = props.archInfo.defaultGroupBy;
        props.Model = makeModelErrorResilient(OneRecordModel);
        props.limit = 1;
        props.Renderer = KanbanEditorRenderer;
        return props;
    },
};
registry.category("studio_editors").add("kanban", kanbanEditor);
