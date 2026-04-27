/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";

import { Component, useState } from "@odoo/owl";
import { useStudioServiceAsReactive } from "@web_studio/studio_service";
const editorTabRegistry = registry.category("web_studio.editor_tabs");

class Breadcrumbs extends Component {
    static template = "web_studio.EditorMenu.Breadcrumbs";
    static props = {
        currentTab: { type: Object },
        switchTab: Function,
    };
    setup() {
        this.editionFlow = useState(this.env.editionFlow);
        this.nextCrumbId = 1;
    }
    get breadcrumbs() {
        const currentTab = this.props.currentTab;
        const crumbs = [
            {
                data: {
                    name: currentTab.name,
                },
                handler: () => this.props.switchTab({ tab: currentTab.id }),
            },
        ];
        const breadcrumbs = this.editionFlow.breadcrumbs;
        breadcrumbs.forEach((crumb) => {
            crumbs.push(crumb);
        });
        for (const crumb of crumbs) {
            crumb.id = this.nextCrumbId++;
        }
        return crumbs;
    }
}

export class EditorMenu extends Component {
    static props = {
        switchTab: Function,
        switchView: Function,
    };
    static template = "web_studio.EditorMenu";
    static viewTypes = [
        {
            title: _t("Form"),
            type: "form",
            iconClasses: "fa fa-address-card",
        },
        {
            title: _t("List"),
            type: "list",
            iconClasses: "oi oi-view-list",
        },
        {
            title: _t("Kanban"),
            type: "kanban",
            iconClasses: "oi oi-view-kanban",
        },
        {
            title: _t("Map"),
            type: "map",
            iconClasses: "fa fa-map-marker",
        },
        {
            title: _t("Calendar"),
            type: "calendar",
            iconClasses: "fa fa-calendar",
        },
        {
            title: _t("Graph"),
            type: "graph",
            iconClasses: "fa fa-area-chart",
        },
        {
            title: _t("Pivot"),
            type: "pivot",
            iconClasses: "oi oi-view-pivot",
        },
        {
            title: _t("Gantt"),
            type: "gantt",
            iconClasses: "fa fa-tasks",
        },
        {
            title: _t("Cohort"),
            type: "cohort",
            iconClasses: "oi oi-view-cohort",
        },
        {
            title: _t("Activity"),
            type: "activity",
            iconClasses: "fa fa-clock-o",
        },
        {
            title: _t("Search"),
            type: "search",
            iconClasses: "oi oi-search",
        },
    ];

    static components = { Breadcrumbs };
    setup() {
        this.l10n = localization;
        this.studio = useStudioServiceAsReactive();
        this.editionFlow = useState(this.env.editionFlow);
    }

    get activeViews() {
        const action = this.studio.editedAction;
        const viewTypes = (action._views || action.views).map(([, type]) => type);
        return this.constructor.viewTypes.filter((vt) => viewTypes.includes(vt.type));
    }

    get editorTabs() {
        const entries = editorTabRegistry.getEntries();
        return entries.map((entry) => Object.assign({}, entry[1], { id: entry[0] }));
    }

    get currentTab() {
        return this.editorTabs.find((tab) => tab.id === this.studio.editorTab);
    }

    openTab(tab) {
        this.props.switchTab({ tab });
    }
}

editorTabRegistry
    .add("views", { name: _t("Views"), action: "web_studio.action_editor" })
    .add("reports", { name: _t("Reports") })
    .add("automations", { name: _t("Automations") })
    .add("automation_webhooks", { name: _t("Webhooks") })
    .add("acl", { name: _t("Access Control") })
    .add("filters", { name: _t("Filter Rules") });
