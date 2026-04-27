/** @odoo-module */

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

const cogMenuRegistry = registry.category("cogMenu");

export class EmbeddedViewActionsMenu extends Component {
    static props = {};
    static template = "knowledge.EmbeddedViewActionsMenu";
    static components = { Dropdown, DropdownItem };

    _onOpenEmbeddedView () {
        this.env.bus.trigger(`KNOWLEDGE_EMBEDDED_${this.env.searchModel.context.knowledgeEmbeddedViewId}:OPEN`);
    }
    _onEditEmbeddedView () {
        this.env.bus.trigger(`KNOWLEDGE_EMBEDDED_${this.env.searchModel.context.knowledgeEmbeddedViewId}:EDIT`);
    }
}

cogMenuRegistry.add(
    'embedded-view-actions-menu',
    {
        Component: EmbeddedViewActionsMenu,
        groupNumber: 10,
        isDisplayed: (env) => {
            /**
             * Those buttons should only be displayed when inside the main Knowledge view.
             * This means that the context should contain an embedded ID and a context key called
             * `isOpenedEmbeddedView`. (Which is added when clicking on the open button)
             */
            return env.searchModel.context.knowledgeEmbeddedViewId &&
                    !env.searchModel.context.isOpenedEmbeddedView;
        },
    },
);
