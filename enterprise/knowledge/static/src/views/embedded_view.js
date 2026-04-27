/** @odoo-module */

import { KnowledgeSearchModelMixin } from "@knowledge/search_model/search_model";
import { SearchModel } from "@web/search/search_model";
import { View } from "@web/views/view";

export class EmbeddedView extends View {
    static props = {
        ...View.props,
        saveEmbeddedViewFavoriteFilter: Function,
        deleteEmbeddedViewFavoriteFilter: Function,
    };

    async loadView(props) {
        const {
            additionalViewProps,
            saveEmbeddedViewFavoriteFilter,
            deleteEmbeddedViewFavoriteFilter,
            ...viewProps
        } = props;
        delete viewProps.displayName;
        Object.assign(viewProps, additionalViewProps);
        await super.loadView(viewProps);
        this.withSearchProps.SearchModel = KnowledgeSearchModelMixin(
            this.withSearchProps.SearchModel || SearchModel
        );
        this.withSearchProps.searchModelArgs = {
            saveEmbeddedViewFavoriteFilter,
            deleteEmbeddedViewFavoriteFilter,
        };
    }

    /**
     * The super method makes the assumption that the props can only vary in
     * the search keys, but we cannot make this assumption with embedded views:
     * the user can edit the additionalViewProps from the embeddedViewComponent
     */
    async onWillUpdateProps(nextProps) {
        super.onWillUpdateProps(nextProps);
        this.env.config.setDisplayName(nextProps.displayName);
        if (
            JSON.stringify(this.props.additionalViewProps) !==
            JSON.stringify(nextProps.additionalViewProps)
        ) {
            Object.assign(this.componentProps, nextProps.additionalViewProps);
        }
    }
}
