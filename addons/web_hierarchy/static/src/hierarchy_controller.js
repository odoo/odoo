import { Component, signal, t, useProps, proxy, computed } from "@odoo/owl";

import { useModel } from "@web/model/model";
import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { useSetupAction } from "@web/search/action_hook";
import { useService } from "@web/core/utils/hooks";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { Layout } from "@web/search/layout";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { standardViewProps } from "@web/views/standard_view_props";
import { executeButtonCallback, useViewButtons } from "@web/views/view_button/view_button_hook";
import { ActionHelper } from "@web/views/action_helper";

import { HierarchyPager } from "./hierarchy_pager";

export class HierarchyController extends Component {
    static components = {
        Layout,
        CogMenu,
        SearchBar,
        ActionHelper,
        HierarchyPager,
    };
    static template = "web_hierarchy.HierarchyView";

    props = useProps({
        ...standardViewProps,
        Model: t.function(),
        Renderer: t.function(),
        buttonTemplate: t.string(),
        archInfo: t.object(),
    });

    rootRef = signal.ref();

    displayNoContent = computed(() => this.model.root?.count === 0);

    setup() {
        const { parentFieldName, childFieldName } = this.props.archInfo;
        const { activeFields, fields } = extractFieldsFromArchInfo(this.props.archInfo, this.props.fields);
        const additionalFields = [{ name: "display_name" }, {name: parentFieldName, type: "many2one"}];
        addFieldDependencies(activeFields, fields, additionalFields);
        const modelConfig = this.props.state?.modelState?.config || {};
        this.model = proxy(useModel(this.props.Model, {
            config: {
                ...modelConfig,
                resModel: this.props.resModel,
                activeFields,
                fields,
            },
            defaultOrderBy: this.props.archInfo.defaultOrder,
            parentFieldName,
            childFieldName,
        }));
        useViewButtons(this.rootRef, {
            reload: this.model.load.bind(this.model),
        });
        useSetupAction({
            rootRef: this.rootRef,
            getLocalState: () => ({
                modelState: this.model.exportState(),
            }),
        });
        this.searchBarToggler = useSearchBarToggler();
        this.uiService = useService("ui");
    }

    openRecord(record, newWindow) {
        const activeIds = this.model.root.records.map((record) => record.resId);
        this.props.selectRecord(record.resId, { activeIds, newWindow });
    }

    async onClickCreate(_ev, newWindow) {
        return executeButtonCallback(this.rootRef(), () => this.props.createRecord(newWindow));
    }

}
