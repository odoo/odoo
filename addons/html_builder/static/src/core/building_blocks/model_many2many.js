import { Component, onWillStart, useEffect, props, proxy, status, t } from "@odoo/owl";
import { uniqueId } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { useDomState, getAllActionsAndOperations } from "@html_builder/core/utils";
import { useCachedModel } from "@html_builder/core/cached_model_utils";
import { BuilderComponent } from "./builder_component";
import { BasicMany2Many } from "./basic_many2many";

export class ModelMany2Many extends Component {
    static template = "html_builder.ModelMany2Many";
    props = props({
        //...basicContainerBuilderComponentProps,
        action: t.string().optional(),
        actionParam: t.any().optional(),
        baseModel: t.string(),
        recordId: t.number(),
        m2oField: t.string(),
        fields: t.array(t.string()).optional([]),
        domain: t.array().optional([]),
        limit: t.number().optional(10),
        createAction: t.string().optional(),
        id: t.string().optional(),
        // currently always allowDelete
        applyTo: t.string().optional(),
    });
    static components = { BuilderComponent, BasicMany2Many };

    setup() {
        this.fields = useService("field");
        this.cachedModel = useCachedModel();
        this.state = proxy({
            searchModel: undefined,
        });
        this.modelEdit = undefined;
        // This `useDomState` is here to get update from history when undo/redo
        this.domState = useDomState((el) => {
            if (!this.modelEdit) {
                return { selection: [] };
            }
            return {
                selection: this.modelEdit.get(this.props.m2oField),
            };
        });
        onWillStart(async () => {
            await this.handleProps(this.props);
        });
        useEffect(() => {
            this.handleProps(this.props);
        });
    }
    async handleProps(props) {
        const { callOperation } = getAllActionsAndOperations(this);
        this.callOperation = callOperation;
        this.applyOperation = this.env.editor.shared.history.makePreviewableAsyncOperation(
            this.callApply.bind(this)
        );
        const [record] = await this.cachedModel.ormRead(
            props.baseModel,
            [props.recordId],
            [props.m2oField]
        );

        if (status(this) === "destroyed") {
            return;
        }

        const selectedRecordIds = record[props.m2oField];
        // TODO: handle no record
        const modelData = await this.fields.loadFields(props.baseModel, {
            fieldNames: [props.m2oField],
        });
        // TODO: simultaneously fly both RPCs
        this.state.searchModel = modelData[props.m2oField].relation;
        this.modelEdit = this.cachedModel.useModelEdit({
            model: this.props.baseModel,
            recordId: props.recordId,
        });
        if (!this.modelEdit.has(props.m2oField)) {
            const storedSelection = await this.cachedModel.ormRead(
                this.state.searchModel,
                selectedRecordIds,
                ["display_name"]
            );
            for (const item of storedSelection) {
                item.name = item.display_name;
            }
            this.modelEdit.init(props.m2oField, [...storedSelection]);
        }
        this.domState.selection = this.modelEdit.get(props.m2oField);
        if (this.props.createAction) {
            try {
                this.createAction = this.env.editor.shared.builderActions.getAction(
                    this.props.createAction
                );
            } catch {
                this.createAction = undefined;
            }
        }
    }
    callApply(applySpecs) {
        const proms = [];
        for (const applySpec of applySpecs) {
            proms.push(
                applySpec.action.apply({
                    editingElement: applySpec.editingElement,
                    params: { ...applySpec.actionParam, oldSelection: this.oldSelection },
                    value: applySpec.actionValue,
                    loadResult: applySpec.loadResult,
                    dependencyManager: this.env.dependencyManager,
                })
            );
        }
        return proms;
    }
    setSelection(newSelection) {
        this.oldSelection = this.modelEdit.get(this.props.m2oField);
        this.modelEdit.set(this.props.m2oField, newSelection);
        this.callOperation(this.applyOperation.commit, {
            userInputValue: JSON.stringify(newSelection),
        });
        this.env.editor.shared.history.commit();
    }
    async create(name) {
        // TODO maybe this can be in base layer
        const loadResult = await this.createAction?.load?.({ value: name });
        this.setSelection([
            ...this.domState.selection,
            {
                id: loadResult || `${uniqueId()}`,
                name: name,
                display_name: name,
                model: this.state.searchModel,
            },
        ]);
    }
}
