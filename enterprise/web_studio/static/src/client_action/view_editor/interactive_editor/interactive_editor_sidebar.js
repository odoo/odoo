/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { onWillStart, useState, onWillUpdateProps, Component } from "@odoo/owl";

import { Notebook } from "@web/core/notebook/notebook";
import { useBus } from "@web/core/utils/hooks";

const tabsDisplay = {
    new: {
        class: "o_web_studio_new px-2",
        title: _t("Add"),
    },
    view: {
        class: "o_web_studio_view px-2",
        title: _t("View"),
    },
    properties: {
        class: "o_web_studio_properties px-2",
        title: _t("Properties"),
    },
};

export class InteractiveEditorSidebar extends Component {
    static components = { Notebook };
    static template = "web_studio.ViewEditor.InteractiveEditorSidebar";
    static props = {
        slots: { type: Object },
    };

    setup() {
        this.editorModel = useState(this.env.viewEditorModel);
        this.tabsDisplay = tabsDisplay;
        useBus(this.editorModel.bus, "error", () => this.render(true));

        this._defaultTab = this.computeDefaultTab(this.props);
        this.editorModel.sidebarTab = this._defaultTab;

        onWillStart(() => {
            this.editorModel.resetSidebar();
        });
        onWillUpdateProps(() => {
            // This component takes slots: it is always re-rendered
            const editorModel = this.editorModel;
            if (editorModel.sidebarTab === "properties" && !editorModel.activeNode) {
                editorModel.resetSidebar();
            }
        });
    }

    get icons() {
        return {
            new: "fa-plus",
            view: "fa-television",
            properties: "fa-server",
        };
    }

    computeDefaultTab(props) {
        const slots = props.slots;
        const defaults = Object.keys(slots).filter((s) => slots[s].isDefault);
        if (defaults.length) {
            return defaults[0];
        }
        return "new" in slots ? "new" : "view";
    }

    get defaultTab() {
        return this.editorModel.sidebarTab || this._defaultTab;
    }

    onTabClicked(tab) {
        if (tab !== "properties") {
            this.editorModel.resetSidebar(tab);
        }
        this.editorModel.sidebarTab = tab;
    }
}
