import { Component, useState } from "@odoo/owl";
import { useService, useAutofocus } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import {
    basicContainerBuilderComponentProps,
    getAllActionsAndOperations,
    useBuilderComponent,
    useDomState,
} from "./utils";
import { BuilderComponent } from "./builder_component";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Dropdown } from "@web/core/dropdown/dropdown";

export class BuilderMany2Many extends Component {
    static template = "html_builder.BuilderMany2Many";
    static props = {
        ...basicContainerBuilderComponentProps,
        model: String,
        fields: { type: Array, element: String, optional: true },
        domain: { type: Array, optional: true },
        limit: Number,
        id: { type: String, optional: true },
        // currently always fakem2m
        // currently always allowDelete
    };
    static defaultProps = {
        ...BuilderComponent.defaultProps,
        fields: [],
        domain: [],
    };
    static components = { BuilderComponent, Dropdown, DropdownItem };

    setup() {
        this.orm = useService("orm");
        useBuilderComponent();
        const { getAllActions, callOperation } = getAllActionsAndOperations(this);
        this.callOperation = callOperation;
        this.applyOperation = this.env.editor.shared.history.makePreviewableOperation(
            this.callApply.bind(this)
        );
        this.selectionToApply = undefined;
        this.domState = useDomState((el) => {
            const getAction = this.env.editor.shared.builderActions.getAction;
            const actionWithGetValue = getAllActions().find(
                ({ actionId }) => getAction(actionId).getValue
            );
            const { actionId, actionParam } = actionWithGetValue;
            const actionValue = getAction(actionId).getValue({
                editingElement: el,
                param: actionParam,
            });
            const selection = JSON.parse(actionValue || "[]");
            return {
                selection: selection,
            };
        });
        this.state = useState({
            searchResults: [],
        });
        this.onSearch = debounce(this.search.bind(this), 300);
        // TODO focus on open dropdown, does not seem to work
        useAutofocus();
    }
    callApply(applySpecs) {
        for (const applySpec of applySpecs) {
            applySpec.apply({
                editingElement: applySpec.editingElement,
                param: applySpec.actionParam,
                value: JSON.stringify(this.selectionToApply),
                loadResult: applySpec.loadResult,
                dependencyManager: this.env.dependencyManager,
            });
        }
    }
    unselect(id) {
        this.selectionToApply = [...this.domState.selection.filter((item) => item.id !== id)];
        this.callOperation(this.applyOperation.commit);
    }
    search(ev) {
        this._search(ev.target.value);
    }
    async _getSearchDomain() {
        // TODO
        return [];
    }
    async _search(needle) {
        const recTuples = await this.orm.call(this.props.model, "name_search", [], {
            name: needle,
            args: (
                await this._getSearchDomain()
            ).concat(Object.values(this.props.domain).filter((item) => item !== null)),
            operator: "ilike",
            limit: this.props.limit + 1,
        });
        this.state.searchResults.length = 0;
        for (const tuple of recTuples) {
            this.state.searchResults.push({
                id: tuple[0],
                name: tuple[1],
            });
        }
        /* TODO handle types
        const records = await this.orm.read(
            this.props.model,
            recTuples.map(([id, _name]) => id),
            this.props.fields
        );
        */
    }
    select(entry) {
        this.selectionToApply = [...this.domState.selection, entry];
        this.callOperation(this.applyOperation.commit);
    }
}
