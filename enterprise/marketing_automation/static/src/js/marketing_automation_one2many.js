/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { append, createElement, parseXML } from "@web/core/utils/xml";
import { useX2ManyCrud, useOpenX2ManyRecord } from "@web/views/fields/relational_utils";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { useEffect, useRef, useSubEnv } from "@odoo/owl";

const fieldRegistry = registry.category("fields");


export class HierarchyKanbanRecord extends KanbanRecord {
    static components = {
        ...KanbanRecord.components,
        HierarchyKanbanRecord,
    };

    static defaultProps = {
        ...KanbanRecord.defaultProps,
    };

    static props = KanbanRecord.props.concat(["is_readonly?", "getRecordDepth"]);

    setup() {
        super.setup();

        this.dialogService = useService("dialog");

        if (this.props.is_readonly !== undefined) {
            this.props.readonly = this.props.is_readonly;
        }

        this.activeTab = 'graph';
        useEffect(
            () => {
                const activityTabs = this.rootRef.el.querySelectorAll('.o_ma_activity_tab');
                const onMarketingActivityTabClick = this.onMarketingActivityTabClick.bind(this);
                activityTabs.forEach((el) => {
                    el.addEventListener("click", onMarketingActivityTabClick);
                });

                return () => {
                    activityTabs.forEach((el) => {
                        el.removeEventListener("click", onMarketingActivityTabClick);
                    });
                };
            },
            () => []
        );

        useEffect(
            this.applyTabPanelVisibility.bind(this),
            () => [this.rootRef.el]
        );

        useEffect(
            () => {
                const addChildActivityButtons = this.rootRef.el.querySelectorAll('.o_add_child_activity');
                const onAddChildActivityClick = this.onAddChildActivityClick.bind(this);
                addChildActivityButtons.forEach((el) => {
                    el.addEventListener("click", onAddChildActivityClick);
                });

                return () => {
                    addChildActivityButtons.forEach((el) => {
                        el.removeEventListener("click", onAddChildActivityClick);
                    });
                };
            },
            () => []
        );
    }

    /**
     * Simply adds a confirmation prompt when deleting a marketing.activity record that has children
     * activities. Since the ORM will then perform a cascade deletion of children.
     */
    triggerAction(params) {
        const { group, list, record } = this.props;
        const listOrGroup = group || list;
        const { type } = params;
        const directChildren = list.records.filter(
            (listRecord) => listRecord.data.parent_id && listRecord.data.parent_id[0] == record.resId
        );

        if (type === "delete" && !listOrGroup.deleteRecords &&
            directChildren && directChildren.length !== 0) {
            this.dialogService.add(ConfirmationDialog, {
                body: _t("Deleting this activity will delete ALL its children activities. Are you sure?"),
                confirmLabel: _t("Delete"),
                confirm: () => super.triggerAction(...arguments),
                cancel: () => {},
            });
        } else {
            super.triggerAction(...arguments);
        }
    }

    //--------------------------------------------------------------------------
    // Business
    //--------------------------------------------------------------------------

    /**
     * Helper method that opens the marketing.activity Form dialog with pre-configured trigger_type
     * and parent_id. Used for the various create buttons on the kanban card footers.
     *
     * @param {MouseEvent} ev
     */
    async onAddChildActivityClick(ev) {
        await this.props.list.model.root.save();

        const context = {
            default_parent_id: this.props.record.resId,
            default_trigger_type: ev.target.dataset.triggerType,
        };
        this.env.onAddMarketingActivity({ context });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Allows to switch between the 'graph' and 'filter' tabs of the activity kanban card.
     *
     * @param {MouseEvent} ev
     */
    onMarketingActivityTabClick(ev) {
        ev.stopPropagation();

        this.activeTab = ev.currentTarget.dataset.tabType;
        this.applyTabPanelVisibility();
        this.props.record.model.notify();  // force chart re-render
    }

    applyTabPanelVisibility() {
        const graphTab = this.rootRef.el.querySelector('.o_pane_graph');
        const filterTab = this.rootRef.el.querySelector('.o_pane_filter');

        if (!graphTab || !filterTab) {
            return;
        }

        this.rootRef.el.querySelectorAll('.o_ma_activity_tab').forEach(
            el => el.classList.remove('active')
        );

        if (this.activeTab === 'graph') {
            graphTab.classList.remove('d-none');
            filterTab.classList.add('d-none');
            const graphTabButton = this.rootRef.el.querySelector('[data-tab-type="graph"]');
            if (graphTabButton) {
                graphTabButton.classList.add('active');
            }
        } else if (this.activeTab === 'filter') {
            graphTab.classList.add('d-none');
            filterTab.classList.remove('d-none');
            const filterTabButton = this.rootRef.el.querySelector('[data-tab-type="filter"]');
            if (filterTabButton) {
                filterTabButton.classList.add('active');
            }
        }
    }
}


export class HierarchyKanbanRenderer extends KanbanRenderer {
    /**
     * Overrides the base setup to enable "parent/children" relationship display.
     *
     * If we have a records list containing (in that order):
     * - Child 1 of Parent 1
     * - Child 2 of Parent 1
     * - Parent 2
     * - Child 1 of Parent 2
     * - Parent 1
     * - Grand-Child 1 (Parent 1 + Child 1)
     *
     * We want it displayed as follows:
     * Parent 1
     * --- Child 1 of Parent 1
     * --- --- Grand-Child 1 (Parent 1 + Child 1)
     * --- Child 2 of Parent 1
     * Parent 2
     * --- Child 1 of Parent 2
     *
     * This involves 3 necessary operations.
     *
     * 1. Adapt the template
     * Which is done to introduce the notion of "depth" and wrap children elements X (=depth) times.
     * This allows to give left padding to the children and display a dotted left-border on those
     * wrappers to give a sense of 'timeline' to the end user.
     * Essentially, for every ancestor this element has, we wrap it into one additional DIV.
     *
     * This is done by recursively calling a wrapper DIV until we reach the depth of the record.
     * (See point 3 for depth explanation).
     *
     * This can NOT be defined in the base XML arch, as the arch definition should be agnostic of
     * this JS class implementation details.
     * (In order to work in studio, be easily extended / migrated, ...)
     *
     * 2. Sort records
     *
     * Records come sorted based on the "interval_standardized" field only.
     * We need to sort them from the first ancestor to its children and the children of its children
     * etc until we reach the appropriate sorting (see example).
     * This is important as records are going to be displayed "on top of each other", as children
     * cannot be wrapped within their parent element.
     *
     * 3. Compute the record "depth"
     *
     * As explained earlier, we need to compute the record depth, which is the number of ancestors
     * this record has.
     * For example, our "Grand-Child 1 (Parent 1 / Child 1)" has a depth of 2.
     *
     */

    static template = "marketing_automation.HierarchyKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: HierarchyKanbanRecord,
    };

    setup() {
        super.setup();

        const rootEl = this.props.archInfo.templateDocs["card"].firstElementChild;
        const rootTemplate = createElement("t", { "t-name": "root" });
        append(rootTemplate, rootEl);
        this.props.archInfo.templateDocs.root = rootTemplate;

        const mainTemplate = parseXML(
            `
            <t t-name="card">
                <t t-set="currentDepth" t-value="currentDepth ? currentDepth + 1 : 1"/>
                <div t-if="__comp__.props.getRecordDepth(__comp__.props.record) - currentDepth + 1 > 0" class="o_ma_body_wrapper"
                    t-call="{{ __comp__.templates['card'] }}"/>
                <t t-else="" t-call="{{ __comp__.templates.root }}"/>
            </t>
            `,
        );

        this.props.archInfo.templateDocs["card"] = mainTemplate;

        this.rootRef = useRef("root");
    }

    getGroupsOrRecords() {
        return this._getSortedRecordsByHierarchy(this.props.list.records, false).map((record) => ({
            record,
            key: record.id,
        }));
    }

    getRecordDepth(record) {
        let parentByChildMap = this._getParentByChildMap(this.props.list.records);
        let childId = record.resId;
        let depth = 0;
        while (childId) {
            childId = parentByChildMap[childId];
            if (childId) {
                depth++;
            }
        }
        return depth;
    }

    /**
     * See 'setup' docstring for details.
     */
    _getParentByChildMap(records) {
        const parentMap = {};
        records.forEach((activityRecord) => {
            const parentId = activityRecord.data.parent_id;
            if (parentId) {
                parentMap[activityRecord.resId] = parentId[0];
            }
        });

        return parentMap;
    }

    /**
     * See 'setup' docstring for details.
     */
    _getSortedRecordsByHierarchy(records, parentId) {
        return records.flatMap(record => {
            if (!record.resId) {
                return []
            } else if (!record.data.parent_id && parentId) {
                return [];
            } else if (record.data.parent_id && record.data.parent_id[0] !== parentId) {
                return [];
            }

            return [record, ...this._getSortedRecordsByHierarchy(records, record.resId)];
        });
    };
}

export class HierarchyKanban extends X2ManyField {
    /**
     * Overrides the "openRecord" method to overload the save.
     *
     * Every time we save a sub-marketing.activity, we want to save the whole marketing.automation
     * record and form view.
     *
     * This allows the end-user to easily chain activities, otherwise he would have to save the
     * enclosing form view in-between each activity addition.
     */

    static components = {
        ...X2ManyField.components,
        KanbanRenderer: HierarchyKanbanRenderer
    };

    setup() {
        super.setup();

        const { saveRecord, updateRecord } = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord: async (record) => {
                await saveRecord(record);
                await this.props.record.save();
            },
            updateRecord: updateRecord,
        });
        this._openRecord = openRecord;

        useSubEnv({
            onAddMarketingActivity: this.onAdd.bind(this),
        });
    }

}

export const hierarchyKanban = {
    ...x2ManyField,
    component: HierarchyKanban,
};

fieldRegistry.add("hierarchy_kanban", hierarchyKanban);
