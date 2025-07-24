import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    getAllActionsAndOperations,
    useBuilderComponent,
    useDependencyDefinition,
    useDomState,
    useHasPreview,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { SelectMany2X } from "./select_many2x";
import { useCachedModel } from "../cached_model_utils";

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
        nullText: { type: String, optional: true },
    };
    static defaultProps = {
        ...BuilderComponent.defaultProps,
        allowUnselect: true,
    };
    static components = { BuilderComponent, SelectMany2X };

    setup() {
        useBuilderComponent();
        const { getAllActions, callOperation } = getAllActionsAndOperations(this);
        this.cachedModel = useCachedModel();
        this.callOperation = callOperation;
        this.hasPreview = useHasPreview(getAllActions);
        this.applyOperation = this.env.editor.shared.history.makePreviewableAsyncOperation(
            this.callApply.bind(this)
        );
        const getAction = this.env.editor.shared.builderActions.getAction;
        const actionWithGetValue = getAllActions().find(
            ({ actionId }) => getAction(actionId).getValue
        );
        const { actionId, actionParam } = actionWithGetValue;
        const getValue = (el) =>
            getAction(actionId).getValue({ editingElement: el, params: actionParam });
        this.domState = useDomState(async (el) => {
            const selectedString = getValue(el);
            const selected = selectedString && JSON.parse(selectedString);
            if (selected && !("display_name" in selected && "name" in selected)) {
                let value;
                if (!selected.id) {
                    value = {
                        display_name: this.props.nullText,
                        name: this.props.nullText,
                    };
                } else {
                    value = (
                        await this.cachedModel.ormRead(
                            this.props.model,
                            [selected.id],
                            ["display_name", "name"]
                        )
                    )[0];
                }
                Object.assign(selected, value);
            }

            return { selected };
        });
        if (this.props.id) {
            useDependencyDefinition(this.props.id, {
                getValue: () => getValue(this.env.getEditingElement()),
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
    callApply(applySpecs, isPreviewing) {
        const proms = [];
        for (const applySpec of applySpecs) {
            if (applySpec.actionValue === undefined) {
                applySpec.action.clean({
                    isPreviewing,
                    editingElement: applySpec.editingElement,
                    params: applySpec.actionParam,
                    dependencyManager: this.env.dependencyManager,
                });
            } else {
                proms.push(
                    applySpec.action.apply({
                        isPreviewing,
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
    preview(newSelected) {
        this.callOperation(this.applyOperation.preview, {
            preview: true,
            userInputValue: newSelected && JSON.stringify(newSelected),
            operationParams: {
                cancellable: true,
                cancelPrevious: () => this.applyOperation.revert(),
            },
        });
    }
    revert() {
        // The `next` will cancel the previous operation, which will revert
        // the operation in case of a preview.
        this.env.editor.shared.operation.next();
    }
    create(name) {
        const args = { editingElement: this.env.getEditingElement(), value: name };
        this.env.editor.shared.operation.next(() => this.createOperation.commit(args), {
            load: () =>
                this.createAction.load?.(args).then((loadResult) => (args.loadResult = loadResult)),
        });
    }
}
