import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    getAllActionsAndOperations,
    useBuilderComponent,
    useDomState,
} from "./utils";
import { BuilderComponent } from "./builder_component";
import { BasicMany2Many } from "./basic_many2many";

export class BuilderMany2Many extends Component {
    static template = "html_builder.BuilderMany2Many";
    static props = {
        ...basicContainerBuilderComponentProps,
        model: String,
        fields: { type: Array, element: String, optional: true },
        domain: { type: Array, optional: true },
        limit: { type: Number, optional: true },
        id: { type: String, optional: true },
    };
    static defaultProps = {
        ...BuilderComponent.defaultProps,
        fields: [],
        domain: [],
        limit: 10,
    };
    static components = { BuilderComponent, BasicMany2Many };

    setup() {
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
            return {
                selection: JSON.parse(actionValue || "[]"),
            };
        });
    }
    callApply(applySpecs) {
        for (const applySpec of applySpecs) {
            applySpec.apply({
                editingElement: applySpec.editingElement,
                param: applySpec.actionParam,
                value: this.selectionToApply,
                loadResult: applySpec.loadResult,
                dependencyManager: this.env.dependencyManager,
            });
        }
    }
    setSelection(newSelection) {
        this.selectionToApply = JSON.stringify(newSelection);
        this.callOperation(this.applyOperation.commit);
    }
}
