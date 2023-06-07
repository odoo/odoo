/** @odoo-module **/

import { deleteConfirmationMessage, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { session } from "@web/session";
import { useSetupView } from "@web/views/view_hook";
import { useModelWithSampleData } from "@web/model/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { MultiRecordViewButton } from "@web/views/view_button/multi_record_view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { KanbanRenderer } from "./kanban_renderer";
import { useProgressBar } from "./progress_bar_hook";

import { Component, reactive, useRef, useState } from "@odoo/owl";

const QUICK_CREATE_FIELD_TYPES = ["char", "boolean", "many2one", "selection", "many2many"];

// -----------------------------------------------------------------------------

export class KanbanController extends Component {
    setup() {
        this.actionService = useService("action");
        this.dialog = useService("dialog");
        const { Model, archInfo } = this.props;

        class KanbanSampleModel extends Model {
            setup() {
                super.setup(...arguments);
                this.initialSampleGroups = undefined;
            }

            /**
             * @override
             */
            hasData() {
                if (this.root.groups) {
                    if (!this.root.groups.length) {
                        // While we don't have any data, we want to display the column quick create and
                        // example background. Return true so that we don't get sample data instead
                        return true;
                    }
                    return this.root.groups.some((group) => group.hasData);
                }
                return super.hasData();
            }

            async load() {
                if (this.orm.isSample && this.initialSampleGroups) {
                    this.orm.setGroups(this.initialSampleGroups);
                }
                return super.load(...arguments);
            }

            async _webReadGroup() {
                const result = await super._webReadGroup(...arguments);
                if (!this.initialSampleGroups) {
                    this.initialSampleGroups = JSON.parse(JSON.stringify(result.groups));
                }
                return result;
            }

            removeSampleDataInGroups() {
                if (this.useSampleModel) {
                    for (const group of this.root.groups) {
                        const list = group.list;
                        group.count = 0;
                        list.count = 0;
                        if (list.records) {
                            list.records = [];
                        } else {
                            list.groups = [];
                        }
                    }
                }
            }
        }

        this.model = useState(
            useModelWithSampleData(KanbanSampleModel, this.modelParams, this.modelOptions)
        );
        if (archInfo.progressAttributes) {
            const { activeBars } = this.props.state || {};
            this.progressBarState = useProgressBar(
                archInfo.progressAttributes,
                this.model,
                this.progressBarAggregateFields,
                activeBars
            );
        }
        this.headerButtons = archInfo.headerButtons;

        const self = this;
        this.quickCreateState = reactive({
            get groupId() {
                return this._groupId || false;
            },
            set groupId(groupId) {
                if (self.model.useSampleModel) {
                    self.model.removeSampleDataInGroups();
                    self.model.useSampleModel = false;
                }
                this._groupId = groupId;
            },
            view: archInfo.quickCreateView,
        });

        this.rootRef = useRef("root");
        useViewButtons(this.model, this.rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
        });
        useSetupView({
            rootRef: this.rootRef,
            getGlobalState: () => {
                return {
                    resIds: this.model.root.records.map((rec) => rec.resId), // WOWL: ask LPE why?
                };
            },
            getLocalState: () => {
                return {
                    activeBars: this.progressBarState?.activeBars,
                    modelState: this.model.exportState(),
                };
            },
        });
        usePager(() => {
            const root = this.model.root;
            const { count, hasLimitedCount, isGrouped, limit, offset } = root;
            if (!isGrouped) {
                return {
                    offset: offset,
                    limit: limit,
                    total: count,
                    onUpdate: async ({ offset, limit }) => {
                        await this.model.root.load({ offset, limit });
                        await this.onUpdatedPager();
                    },
                    updateTotal: hasLimitedCount ? () => root.fetchCount() : undefined,
                };
            }
        });
        this.searchBarToggler = useSearchBarToggler();
    }

    get modelParams() {
        const { resModel, archInfo, limit, defaultGroupBy } = this.props;
        const { activeFields, fields } = extractFieldsFromArchInfo(archInfo, this.props.fields);
        addFieldDependencies(activeFields, fields, this.progressBarAggregateFields);
        const modelConfig = this.props.state?.modelState?.config || {
            resModel,
            activeFields,
            fields,
            openGroupsByDefault: true,
        };

        return {
            config: modelConfig,
            state: this.props.state?.modelState,
            limit: archInfo.limit || limit || 40,
            groupsLimit: Number.MAX_SAFE_INTEGER, // no limit
            countLimit: archInfo.countLimit,
            defaultGroupBy,
            defaultOrderBy: archInfo.defaultOrder,
            maxGroupByDepth: 1,
            activeIdsLimit: session.active_ids_limit,
            hooks: {
                onRecordSaved: this.onRecordSaved.bind(this),
            },
        };
    }

    get modelOptions() {
        return {};
    }

    get progressBarAggregateFields() {
        const res = [];
        const { progressAttributes } = this.props.archInfo;
        if (progressAttributes && progressAttributes.sumField) {
            res.push(progressAttributes.sumField);
        }
        return res;
    }

    get className() {
        if (this.env.isSmall && this.model.root.isGrouped) {
            const classList = (this.props.className || "").split(" ");
            classList.push("o_action_delegate_scroll");
            return classList.join(" ");
        }
        return this.props.className;
    }

    async deleteRecord(record) {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Bye-bye, record!"),
            body: deleteConfirmationMessage,
            confirm: () => this.model.root.deleteRecords([record]),
            confirmLabel: _t("Delete"),
            cancel: () => {},
            cancelLabel: _t("No, keep it"),
        });
    }

    evalViewModifier(modifier) {
        return evaluateBooleanExpr(modifier, { context: this.props.context });
    }

    async openRecord(record, mode) {
        const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds, mode });
    }

    async createRecord() {
        const { onCreate } = this.props.archInfo;
        const { root } = this.model;
        if (this.canQuickCreate && onCreate === "quick_create") {
            const firstGroup = root.groups[0];
            if (firstGroup.isFolded) {
                await firstGroup.toggle();
            }
            this.quickCreateState.groupId = firstGroup.id;
        } else if (onCreate && onCreate !== "quick_create") {
            const options = {
                additionalContext: root.context,
                onClose: async () => {
                    await root.load();
                    this.model.useSampleModel = false;
                    this.render(true); // FIXME WOWL reactivity
                },
            };
            await this.actionService.doAction(onCreate, options);
        } else {
            await this.props.createRecord();
        }
    }

    get canCreate() {
        const { create, createGroup } = this.props.archInfo.activeActions;
        const list = this.model.root;
        if (!create) {
            return false;
        }
        return list.isGrouped ? list.groups.length > 0 || !createGroup : true;
    }

    get canQuickCreate() {
        const { activeActions } = this.props.archInfo;
        if (!activeActions.quickCreate) {
            return false;
        }

        const list = this.model.root;
        if (list.groups && !list.groups.length) {
            return false;
        }

        return this.isQuickCreateField(list.groupByField);
    }

    onRecordSaved(record) {
        if (this.model.root.isGrouped) {
            const group = this.model.root.groups.find((l) =>
                l.records.find((r) => r.id === record.id)
            );
            this.progressBarState?.updateCounts(group);
        }
    }

    async beforeExecuteActionButton(clickParams) {}

    async afterExecuteActionButton(clickParams) {}

    async onUpdatedPager() {}

    scrollTop() {
        this.rootRef.el.querySelector(".o_content").scrollTo({ top: 0 });
    }

    isQuickCreateField(field) {
        return field && QUICK_CREATE_FIELD_TYPES.includes(field.type);
    }
}

KanbanController.template = `web.KanbanView`;
KanbanController.components = { Layout, KanbanRenderer, MultiRecordViewButton, SearchBar, CogMenu };
KanbanController.props = {
    ...standardViewProps,
    defaultGroupBy: {
        validate: (dgb) => !dgb || typeof dgb === "string",
        optional: true,
    },
    editable: { type: Boolean, optional: true },
    forceGlobalClick: { type: Boolean, optional: true },
    onSelectionChanged: { type: Function, optional: true },
    showButtons: { type: Boolean, optional: true },
    Compiler: { type: Function, optional: true }, // optional in stable for backward compatibility
    Model: Function,
    Renderer: Function,
    buttonTemplate: String,
    archInfo: Object,
};

KanbanController.defaultProps = {
    createRecord: () => {},
    forceGlobalClick: false,
    selectRecord: () => {},
    showButtons: true,
};
