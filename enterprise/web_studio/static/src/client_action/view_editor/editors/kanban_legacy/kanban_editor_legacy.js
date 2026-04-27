/** @odoo-module */
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanEditorRendererLegacy } from "@web_studio/client_action/view_editor/editors/kanban_legacy/kanban_editor_renderer_legacy";
import { makeModelErrorResilient } from "@web_studio/client_action/view_editor/editors/utils";
import { KanbanEditorSidebarLegacy } from "./kanban_editor_sidebar_legacy/kanban_editor_sidebar_legacy";
import { getStudioNoFetchFields, useModelConfigFetchInvisible } from "../utils";

class EditorArchParser extends kanbanView.ArchParser {
    parse(arch, models, modelName) {
        const parsed = super.parse(...arguments);
        const noFetch = getStudioNoFetchFields(parsed.fieldNodes);
        parsed.fieldNodes = omit(parsed.fieldNodes, ...noFetch.fieldNodes);
        parsed.progressAttributes = false;
        parsed.canOpenRecords = false;
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

class KanbanEditorControllerLegacy extends kanbanView.Controller {
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
    Controller: KanbanEditorControllerLegacy,
    ArchParser: EditorArchParser,
    Renderer: KanbanEditorRendererLegacy,
    Model: OneRecordModel,
    Sidebar: KanbanEditorSidebarLegacy,
    props(genericProps, editor, config) {
        const props = kanbanView.props(genericProps, editor, config);
        props.defaultGroupBy = props.archInfo.defaultGroupBy;
        props.Model = makeModelErrorResilient(OneRecordModel);
        props.limit = 1;
        props.Renderer = KanbanEditorRendererLegacy;
        return props;
    },
};
registry.category("studio_editors").add("kanban_legacy", kanbanEditor);
