import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    getAllActionsAndOperations,
    revertPreview,
    useBuilderComponent,
    useDependencyDefinition,
    useDomState,
    useHasPreview,
    useOperationWithReload,
    useReloadAction,
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
        unselectBtnTitle: { type: String, optional: true },
        defaultMessage: { type: String, optional: true },
        createAction: { type: String, optional: true },
        nullText: { type: String, optional: true },
    };
    static defaultProps = {
        ...BuilderComponent.defaultProps,
        allowUnselect: true,
        unselectBtnTitle: "Unselect",
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
        // Detect if any action requires a reload.
        const { reload } = useReloadAction(getAllActions);
        this.reload = reload;
        this.operationWithReload = useOperationWithReload(this.callApply.bind(this), reload);
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
        const args = { userInputValue: newSelected && JSON.stringify(newSelected) };
        if (this.reload) {
            this.callOperation(this.operationWithReload, args);
        } else {
            this.callOperation(this.applyOperation.commit, args);
        }
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
        revertPreview(this.env.editor);
    }
    create(name) {
        const args = { editingElement: this.env.getEditingElement(), value: name };
        this.env.editor.shared.operation.next(() => this.createOperation.commit(args), {
            load: () =>
                this.createAction.load?.(args).then((loadResult) => (args.loadResult = loadResult)),
        });
    }
}
