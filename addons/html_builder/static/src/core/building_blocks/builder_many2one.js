import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    getAllActionsAndOperations,
    useBuilderComponent,
    useDependencyDefinition,
    useDomState,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { BasicMany2One } from "./basic_many2one";

export class BuilderMany2One extends Component {
    static template = "html_builder.BuilderMany2One";
    static props = {
        ...basicContainerBuilderComponentProps,
        model: String,
        fields: { type: Array, element: String, optional: true },
        domain: { type: Array, optional: true },
        limit: { type: Number, optional: true },
        id: { type: String, optional: true },
        allowUnselect: { type: Boolean, optional: true },
        defaultMessage: { type: String, optional: true },
        createAction: { type: String, optional: true },
    };
    static defaultProps = {
        ...BuilderComponent.defaultProps,
        allowUnselect: true,
    };
    static components = { BuilderComponent, BasicMany2One };

    setup() {
        useBuilderComponent();
        const { getAllActions, callOperation } = getAllActionsAndOperations(this);
        this.callOperation = callOperation;
        this.applyOperation = this.env.editor.shared.history.makePreviewableOperation(
            this.callApply.bind(this)
        );
        const getAction = this.env.editor.shared.builderActions.getAction;
        const actionWithGetValue = getAllActions().find(
            ({ actionId }) => getAction(actionId).getValue
        );
        const { actionId, actionParam } = actionWithGetValue;
        this.domState = useDomState((el) => {
            const actionValue = getAction(actionId).getValue({
                editingElement: el,
                params: actionParam,
            });
            return { selected: actionValue && JSON.parse(actionValue) };
        });
        if (this.props.id) {
            useDependencyDefinition(this.props.id, {
                getValue: () => this.domState.selected && JSON.stringify(this.domState.selected),
            });
        }

        if (this.props.createAction) {
            this.createAction = this.env.editor.shared.builderActions.getAction(
                this.props.createAction
            );
            this.createOperation = this.env.editor.shared.history.makePreviewableOperation(
                this.createAction.apply
            );
        }
    }
    callApply(applySpecs) {
        const proms = [];
        for (const applySpec of applySpecs) {
            if (applySpec.clean && applySpec.actionValue === undefined) {
                applySpec.clean({
                    editingElement: applySpec.editingElement,
                    params: applySpec.actionParam,
                    dependencyManager: this.env.dependencyManager,
                });
            } else {
                proms.push(
                    applySpec.apply({
                        editingElement: applySpec.editingElement,
                        params: applySpec.actionParam,
                        value: applySpec.actionValue,
                        loadResult: applySpec.loadResult,
                        dependencyManager: this.env.dependencyManager,
                    })
                );
            }
        }
        return Promise.all(proms);
    }
    select(newSelected) {
        this.callOperation(this.applyOperation.commit, {
            userInputValue: newSelected && JSON.stringify(newSelected),
        });
    }
    create(name) {
        const args = { editingElement: this.env.getEditingElement(), value: name };
        this.env.editor.shared.operation.next(() => this.createOperation.commit(args), {
            load: () =>
                this.createAction.load?.(args).then((loadResult) => (args.loadResult = loadResult)),
        });
    }
}
