import { Component, signal, t, useProps, proxy } from "@odoo/owl";

import { useModel } from "@web/model/model";
import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { useSetupAction } from "@web/search/action_hook";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { Layout } from "@web/search/layout";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { standardViewProps } from "@web/views/standard_view_props";
import { executeButtonCallback, useViewButtons } from "@web/views/view_button/view_button_hook";
import { ActionHelper } from "@web/views/action_helper";

export class HierarchyController extends Component {
    static components = {
        Layout,
        CogMenu,
        SearchBar,
        ActionHelper,
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

    setup() {
        const { parentFieldName, childFieldName } = this.props.archInfo;
        const { activeFields, fields } = extractFieldsFromArchInfo(
            this.props.archInfo,
            this.props.fields
        );
        const additionalFields = [{ name: parentFieldName }];
        if (childFieldName) {
            additionalFields.push({ name: childFieldName });
        }
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
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
            reload: this.model.load.bind(this.model),
        });
        useSetupAction({
            rootRef: this.rootRef,
            getLocalState: () => ({
                modelState: this.model.exportState(),
            }),
        });
        this.searchBarToggler = useSearchBarToggler();
    }
    get displayNoContent() {
        return this.model.root?.count === 0;
    }

    async openRecord(record, newWindow) {
        const activeIds = this.model.root.records.map((record) => record.resId);
        this.props.selectRecord(record.resId, { activeIds, newWindow });
    }

    async beforeExecuteActionButton(clickParams) {}

    async afterExecuteActionButton(clickParams) {}

    async onClickCreate(_ev, newWindow) {
        return executeButtonCallback(this.rootRef(), () => this.props.createRecord(newWindow));
    }

}
