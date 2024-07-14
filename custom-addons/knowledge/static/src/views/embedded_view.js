/** @odoo-module */

import { KnowledgeSearchModelMixin } from "@knowledge/search_model/search_model";
import { SearchModel } from "@web/search/search_model";
import { View } from "@web/views/view";

export class EmbeddedView extends View {
    static props = {
        ...View.props,
        onSaveKnowledgeFavorite: Function,
        onDeleteKnowledgeFavorite: Function,
    };

    async loadView(props) {
        const {additionalViewProps, onDeleteKnowledgeFavorite, onSaveKnowledgeFavorite, ...viewProps} = props;
        Object.assign(viewProps, additionalViewProps);
        await super.loadView(viewProps);
        this.withSearchProps.SearchModel = KnowledgeSearchModelMixin(
            this.withSearchProps.SearchModel || SearchModel
        );
        this.withSearchProps.searchModelArgs = {
            onSaveKnowledgeFavorite,
            onDeleteKnowledgeFavorite,
        };
    }

    /**
     * The super method makes the assumption that the props can only vary in
     * the search keys, but we cannot make this assumption with embedded views:
     * the user can edit the additionalViewProps from the embedded view manager
     */
    async onWillUpdateProps(nextProps) {
        super.onWillUpdateProps(nextProps);
        if (JSON.stringify(this.props.additionalViewProps) !== JSON.stringify(nextProps.additionalViewProps)) {
            Object.assign(this.componentProps, nextProps.additionalViewProps);
        }
    }
}
