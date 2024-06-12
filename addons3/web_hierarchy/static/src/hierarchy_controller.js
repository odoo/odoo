/** @odoo-module */

import { Component, useRef } from "@odoo/owl";

import { useBus } from "@web/core/utils/hooks";
import { useModel } from "@web/model/model";
import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { Layout } from "@web/search/layout";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { standardViewProps } from "@web/views/standard_view_props";
import { useViewButtons } from "@web/views/view_button/view_button_hook";

export class HierarchyController extends Component {
    static components = {
        Layout,
        CogMenu,
        SearchBar,
    };
    static props = {
        ...standardViewProps,
        Model: Function,
        Renderer: Function,
        buttonTemplate: String,
        archInfo: Object,
    };
    static template = "web_hierarchy.HierarchyView";

    setup() {
        this.rootRef = useRef("root");
        const { parentFieldName, childFieldName } = this.props.archInfo;
        const { activeFields, fields } = extractFieldsFromArchInfo(this.props.archInfo, this.props.fields);
        addFieldDependencies(activeFields, fields, [{ name: parentFieldName }]);
        this.model = useModel(this.props.Model, {
            resModel: this.props.resModel,
            activeFields,
            fields,
            parentFieldName,
            childFieldName,
        });
        useBus(
            this.model.bus,
            "update",
            () => {
                this.render(true);
            }
        );
        useViewButtons(this.model, this.rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
        });
        this.searchBarToggler = useSearchBarToggler();
    }

    async openRecord(node, mode) {
        const activeIds = this.model.root.resIds;
        this.props.selectRecord(node.resId, { activeIds, mode });
    }

    async beforeExecuteActionButton(clickParams) {}

    async afterExecuteActionButton(clickParams) {}
}
