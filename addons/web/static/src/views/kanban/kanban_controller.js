import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { useSetupAction } from "@web/search/action_hook";
import { ActionMenus, STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { session } from "@web/session";
import { useModelWithSampleData } from "@web/model/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { MultiRecordViewButton } from "@web/views/view_button/multi_record_view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { useExportRecords, useDeleteRecords } from "@web/views/view_hook";
import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { KanbanCogMenu } from "./kanban_cog_menu";
import { KanbanRenderer } from "./kanban_renderer";
import { useProgressBar } from "./progress_bar_hook";
import { SelectionBox } from "@web/views/view_components/selection_box";

import {
    Component,
    onMounted,
    onWillStart,
    reactive,
    useEffect,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";

const QUICK_CREATE_FIELD_TYPES = ["char", "boolean", "many2one", "selection", "many2many"];

// -----------------------------------------------------------------------------

export class KanbanController extends Component {
    static template = `web.KanbanView`;
    static components = {
        ActionMenus,
        DropdownItem,
        Layout,
        KanbanRenderer,
        MultiRecordViewButton,
        SearchBar,
        CogMenu: KanbanCogMenu,
        SelectionBox,
    };
    static props = {
        ...standardViewProps,
        editable: { type: Boolean, optional: true },
        forceGlobalClick: { type: Boolean, optional: true },
        onSelectionChanged: { type: Function, optional: true },
        readonly: { type: Boolean, optional: true },
        showButtons: { type: Boolean, optional: true },
        Compiler: Function,
        Model: Function,
        Renderer: Function,
        buttonTemplate: String,
        archInfo: Object,
    };

    static defaultProps = {
        createRecord: () => {},
        forceGlobalClick: false,
        selectRecord: () => {},
        showButtons: true,
    };

    setup() {
        this.actionService = useService("action");
        this.dialog = useService("dialog");
        const { Model, archInfo } = this.props;

        class KanbanSampleModel extends Model {
            /**
             * @override
             */
            hasData() {
                if (this.root.groups && !this.root.groups.length) {
                    // While we don't have any data, we want to display the column quick create and
                    // example background. Return true so that we don't get sample data instead
                    return true;
                }
                return super.hasData();
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
        useViewButtons(this.rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
            reload: () => this.model.load(),
        });
        const { setScrollFromState } = useSetupAction({
            rootRef: this.rootRef,
            beforeUnload: this.beforeUnload.bind(this),
            beforeLeave: this.beforeLeave.bind(this),
            getLocalState: () => {
                const state = {
                    activeBars: this.progressBarState?.activeBars,
                    modelState: this.model.exportState(),
                };
                if (this.env.isSmall && this.model.root.isGrouped) {
                    const columnScrollTops = [];
                    const sel = ".o_kanban_group:not(.o_column_folded)";
                    const columnEls = this.rootRef.el.querySelectorAll(sel);
                    const groups = this.model.root.groups;
                    for (const columnEl of columnEls) {
                        const scrollTop = columnEl.scrollTop;
                        if (scrollTop > 0) {
                            const group = groups.find((g) => g.id === columnEl.dataset.id);
                            columnScrollTops.push([group.serverValue, columnEl.scrollTop]);
                        }
                    }
                    state.scrollPositions = {
                        scrollLeft: this.rootRef.el.querySelector(".o_renderer")?.scrollLeft || 0,
                        columnScrollTops,
                    };
                }
                return state;
            },
        });
        useEffect(
            (isReady) => {
                if (isReady) {
                    if (this.env.isSmall && this.model.root.isGrouped) {
                        const { scrollPositions } = this.props.state || {};
                        if (scrollPositions) {
                            const { scrollLeft, columnScrollTops } = scrollPositions;
                            this.rootRef.el.querySelector(".o_renderer").scrollLeft = scrollLeft;
                            const groups = this.model.root.groups;
                            for (const [serverValue, scrollTop] of columnScrollTops) {
                                const group = groups.find((g) => g.serverValue === serverValue);
                                if (group) {
                                    const sel = `.o_kanban_group[data-id=${group.id}]`;
                                    this.rootRef.el.querySelector(sel).scrollTop = scrollTop;
                                }
                            }
                        }
                    } else {
                        setScrollFromState();
                    }
                }
            },
            () => [this.model.isReady]
        );
        usePager(() => {
            const root = this.model.root;
            const { count, hasLimitedCount, isGrouped, limit, offset } = root;
            if (!isGrouped && !this.model.useSampleModel) {
                return {
                    offset: offset,
                    limit: limit,
                    total: count,
                    onUpdate: async ({ offset, limit }, hasNavigated) => {
                        await this.model.root.load({ offset, limit });
                        await this.onUpdatedPager();
                        if (hasNavigated) {
                            this.onPageChangeScroll();
                        }
                    },
                    updateTotal: hasLimitedCount ? () => root.fetchCount() : undefined,
                };
            }
        });
        this.searchBarToggler = useSearchBarToggler();
        this.firstLoad = true;
        onMounted(() => {
            this.firstLoad = false;
        });
        useEffect(
            () => {
                this.onSelectionChanged();
            },
            () => [this.model.root.selection?.length, this.model.root.isDomainSelected]
        );
        onWillStart(async () => {
            this.isExportEnable = await user.hasGroup("base.group_allow_export");
        });
        this.archiveEnabled =
            "active" in this.props.fields
                ? !this.props.fields.active.readonly
                : "x_active" in this.props.fields
                ? !this.props.fields.x_active.readonly
                : false;
        useSubEnv({ model: this.model });
        this.exportRecords = useExportRecords(this.env, this.props.context, () =>
            this.getExportableFields()
        );
        this.deleteRecordsWithConfirmation = useDeleteRecords(this.model);
    }

    get display() {
        const { controlPanel } = this.props.display;
        if (!controlPanel) {
            return this.props.display;
        }
        return {
            ...this.props.display,
            controlPanel: {
                ...controlPanel,
                layoutActions: !this.hasSelectedRecords,
            },
        };
    }

    get actionMenuItems() {
        const { actionMenus } = this.props.info;
        const staticActionItems = Object.entries(this.getStaticActionMenuItems())
            .filter(([key, item]) => item.isAvailable === undefined || item.isAvailable())
            .sort(([k1, item1], [k2, item2]) => (item1.sequence || 0) - (item2.sequence || 0))
            .map(([key, item]) =>
                Object.assign(
                    { key, groupNumber: STATIC_ACTIONS_GROUP_NUMBER },
                    omit(item, "isAvailable")
                )
            );

        return {
            action: [...staticActionItems, ...(actionMenus?.action || [])],
            print: actionMenus?.print,
        };
    }

    get actionMenuProps() {
        return {
            getActiveIds: () => this.model.root.selection.map((r) => r.resId),
            context: this.model.root.context,
            domain: this.props.domain,
            items: this.actionMenuItems,
            isDomainSelected: this.model.root.isDomainSelected,
            resModel: this.model.root.resModel,
            onActionExecuted: ({ noReload } = {}) => {
                if (!noReload) {
                    return this.model.load();
                }
            },
        };
    }

    get hasSelectedRecords() {
        return this.model.root.selection?.length || this.isDomainSelected;
    }

    get isDomainSelected() {
        return this.model.root.isDomainSelected;
    }

    get modelParams() {
        const { resModel, archInfo, limit } = this.props;
        const { activeFields, fields } = extractFieldsFromArchInfo(archInfo, this.props.fields);

        const cardColorField = archInfo.cardColorField;
        if (cardColorField) {
            addFieldDependencies(activeFields, fields, [{ name: cardColorField, type: "integer" }]);
        }

        addFieldDependencies(activeFields, fields, this.progressBarAggregateFields);
        const modelConfig = this.props.state?.modelState?.config || {
            resModel,
            activeFields,
            fields,
            fieldsToAggregate: this.progressBarAggregateFields.map((field) => field.name),
            openGroupsByDefault: true,
        };

        return {
            config: modelConfig,
            state: this.props.state?.modelState,
            limit: archInfo.limit || limit || 40,
            groupsLimit: Number.MAX_SAFE_INTEGER, // no limit
            countLimit: archInfo.countLimit,
            defaultOrderBy: archInfo.defaultOrder,
            maxGroupByDepth: 1,
            activeIdsLimit: session.active_ids_limit,
            hooks: {
                onRecordSaved: this.onRecordSaved.bind(this),
            },
        };
    }

    get modelOptions() {
        return {
            lazy:
                !this.env.config.isReloadingController &&
                !this.env.inDialog &&
                !!this.props.display.controlPanel,
        };
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

    get archiveDialogProps() {
        return {};
    }

    get deleteConfirmationDialogProps() {
        return {};
    }

    getExportableFields() {
        return Object.keys(this.model.root.config.activeFields)
            .map((e) => this.props.fields[e])
            .filter((field) => field.type !== "properties");
    }

    async onSelectionChanged() {
        if (this.props.onSelectionChanged) {
            const resIds = await this.model.root.getResIds(true);
            this.props.onSelectionChanged(resIds);
        }
    }

    getStaticActionMenuItems() {
        return {
            export: {
                isAvailable: () => this.isExportEnable,
                sequence: 10,
                icon: "fa fa-upload",
                description: _t("Export"),
                callback: () => this.exportRecords(),
            },
            duplicate: {
                isAvailable: () => this.props.archInfo.activeActions.duplicate,
                sequence: 30,
                icon: "fa fa-clone",
                description: _t("Duplicate"),
                callback: () => this.model.root.duplicateRecords(),
            },
            archive: {
                isAvailable: () => this.archiveEnabled,
                sequence: 40,
                icon: "oi oi-archive",
                description: _t("Archive"),
                callback: () =>
                    this.model.root.toggleArchiveWithConfirmation(true, this.archiveDialogProps),
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled,
                sequence: 45,
                icon: "oi oi-unarchive",
                description: _t("Unarchive"),
                callback: () => this.model.root.toggleArchiveWithConfirmation(false),
            },
            delete: {
                isAvailable: () => this.props.archInfo.activeActions.delete,
                sequence: 50,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                class: "text-danger",
                callback: () =>
                    this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps),
            },
        };
    }

    async beforeUnload() {}

    async beforeLeave() {
        // wait for potential pending write operations (e.g. records being moved)
        return this.model.mutex.getUnlockedDef();
    }

    evalViewModifier(modifier) {
        return evaluateBooleanExpr(modifier, { context: this.props.context });
    }

    deleteRecord(record) {
        this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps, [record]);
    }

    async openRecord(record, { newWindow } = {}) {
        const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.props.selectRecord(record.resId, { activeIds, newWindow });
    }

    async createRecord() {
        const { onCreate } = this.props.archInfo;
        const { root } = this.model;
        if (this.canQuickCreate && onCreate === "quick_create") {
            const firstGroup = root.groups.find((group) => !group.isFolded) || root.groups[0];
            if (firstGroup.isFolded) {
                await firstGroup.toggle();
            }
            this.quickCreateState.groupId = firstGroup.id;
        } else if (onCreate && onCreate !== "quick_create") {
            const options = {
                additionalContext: root.context,
                onClose: async ({ noReload } = {}) => {
                    if (!noReload) {
                        await root.load();
                        this.model.useSampleModel = false;
                        this.render(true); // FIXME WOWL reactivity
                    }
                },
            };
            await this.actionService.doAction(onCreate, options);
        } else {
            await this.props.createRecord();
        }
    }

    get canCreate() {
        return this.props.archInfo.activeActions.create;
    }

    get isNewButtonDisabled() {
        const { createGroup } = this.props.archInfo.activeActions;
        const list = this.model.root;
        return (
            this.model.isReady &&
            list.isGrouped &&
            list.groupByField.type === "many2one" &&
            list.groups.length === 0 &&
            createGroup
        );
    }

    get canQuickCreate() {
        const { activeActions } = this.props.archInfo;
        if (!activeActions.quickCreate) {
            return false;
        }
        if (!this.model.isReady) {
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

    onPageChangeScroll() {
        if (this.rootRef && this.rootRef.el) {
            if (this.env.isSmall) {
                this.rootRef.el.scrollTop = 0;
            } else {
                this.rootRef.el.querySelector(".o_content").scrollTop = 0;
            }
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
