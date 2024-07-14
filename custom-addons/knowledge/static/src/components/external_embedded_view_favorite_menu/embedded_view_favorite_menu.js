/** @odoo-module */

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { supportedEmbeddedViews } from "@knowledge/components/external_embedded_view_insertion/views_renderers_patches";
import { Component } from "@odoo/owl";

const cogMenuRegistry = registry.category("cogMenu");

export class InsertEmbeddedViewMenu extends Component {
    _onInsertEmbeddedViewInArticle () {
        this.env.searchModel.trigger('insert-embedded-view');
    }
    _onInsertViewLinkInArticle () {
        this.env.searchModel.trigger('insert-view-link');
    }
}

InsertEmbeddedViewMenu.props = {};
InsertEmbeddedViewMenu.template = 'knowledge.InsertEmbeddedViewMenu';
InsertEmbeddedViewMenu.components = { Dropdown, DropdownItem };

cogMenuRegistry.add(
    'insert-embedded-view-menu',
    {
        Component: InsertEmbeddedViewMenu,
        groupNumber: 10,
        isDisplayed: (env) => {
            // only support act_window with an id for now, but act_window
            // object could potentially be used too (rework backend API to insert
            // views in articles)
            return env.config.actionId && !env.searchModel.context.knowledgeEmbeddedViewId &&
                supportedEmbeddedViews.has(env.config.viewType);
        },
    },
);
