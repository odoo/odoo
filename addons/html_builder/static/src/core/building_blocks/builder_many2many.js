import { Component, asyncComputed, onWillStart, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import {
    basicContainerBuilderComponentProps,
    getAllActionsAndOperations,
    useBuilderComponent,
    useDomState,
} from "../utils";
import { BasicMany2Many } from "./basic_many2many";
import { BuilderComponent } from "./builder_component";
import { useCachedModel } from "../cached_model_utils";

export class BuilderMany2Many extends Component {
    static components = { BuilderComponent, BasicMany2Many };
    static template = "html_builder.BuilderMany2Many";

    props = useProps({
        ...basicContainerBuilderComponentProps,
        model: t.string(),
        m2oField: t.string().optional(),
        fields: t.array(t.string()).optional(),
        domain: t.array().optional(),
        limit: t.number().optional(),
        displayNameField: t.string().optional("display_name"),
        message: t.string().optional(),
    });

    setup() {
        useBuilderComponent(this.props);
        this.fields = useService("field");
        const { getAllActions, callOperation } = getAllActionsAndOperations(this.props);
        this.cachedModel = useCachedModel();
        this.callOperation = callOperation;
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
            const selectionString = getValue(el);
            const selection = JSON.parse(selectionString || "[]");
            const selectedWithMissingName = selection.filter(
                (e) => !("display_name" in e && "name" in e)
            );
            if (selectedWithMissingName.length) {
                await this.searchModel.currentPromise();
                const namedValues = await this.cachedModel.ormRead(
                    this.searchModel(),
                    selectedWithMissingName.map((e) => e.id),
                    ["display_name", "name"]
                );
                const nameMap = new Map(namedValues.map((e) => [e.id, e]));
                for (const e of selectedWithMissingName) {
                    e.name ||= nameMap.get(e.id).name;
                    e.display_name ||= nameMap.get(e.id).display_name;
                }
            }
            return { selection };
        });
        this.searchModel = asyncComputed(() => this.getSearchModel(this.props));
        onWillStart(() => this.searchModel.currentPromise());
    }
    async getSearchModel(props) {
        if (props.m2oField) {
            const modelData = await this.fields.loadFields(props.model, {
                fieldNames: [props.m2oField],
            });
            const searchModel = modelData[props.m2oField].relation;
            if (!searchModel) {
                throw new Error(`m2oField ${props.m2oField} is not a relation field`);
            }
            return searchModel;
        } else {
            return props.model;
        }
    }
    callApply(applySpecs) {
        const proms = [];
        for (const applySpec of applySpecs) {
            proms.push(
                applySpec.action.apply({
                    editingElement: applySpec.editingElement,
                    params: applySpec.actionParam,
                    value: applySpec.actionValue,
                    loadResult: applySpec.loadResult,
                    dependencyManager: this.env.dependencyManager,
                })
            );
        }
        return proms;
    }
    setSelection(newSelection) {
        this.callOperation(this.applyOperation.commit, {
            userInputValue: JSON.stringify(newSelection),
        });
    }
}
