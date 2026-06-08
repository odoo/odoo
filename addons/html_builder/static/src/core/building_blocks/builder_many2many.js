import { Component, onWillStart, onWillUpdateProps, props, proxy, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { getAllActionsAndOperations, useBuilderComponent, useDomState } from "../utils";
import { BuilderComponent } from "./builder_component";
import { BasicMany2Many } from "./basic_many2many";

export class BuilderMany2Many extends Component {
    static template = "html_builder.BuilderMany2Many";
    props = props({
        // basicContainerBuilderComponentProps (converted inline)
        id: t.string().optional(),
        applyTo: t.string().optional(),
        preview: t.boolean().optional(),
        inheritedActions: t.array(t.string()).optional(),

        action: t.string().optional(),
        actionParam: t.any().optional(),

        // Shorthand actions.
        classAction: t.any().optional(),
        attributeAction: t.any().optional(),
        dataAttributeAction: t.any().optional(),
        styleAction: t.any().optional(),

        model: t.string(),
        m2oField: t.string().optional(),
        fields: t.array(t.string()).optional(),
        domain: t.array().optional(),
        limit: t.number().optional(),
    });
    static components = { BuilderComponent, BasicMany2Many };

    setup() {
        useBuilderComponent();
        this.fields = useService("field");
        const { getAllActions, callOperation } = getAllActionsAndOperations(this);
        this.callOperation = callOperation;
        this.applyOperation = this.env.editor.shared.history.makePreviewableAsyncOperation(
            this.callApply.bind(this)
        );
        this.state = proxy({
            searchModel: undefined,
        });
        this.domState = useDomState((el) => {
            const getAction = this.env.editor.shared.builderActions.getAction;
            const actionWithGetValue = getAllActions().find(
                ({ actionId }) => getAction(actionId).getValue
            );
            const { actionId, actionParam } = actionWithGetValue;
            const actionValue = getAction(actionId).getValue({
                editingElement: el,
                params: actionParam,
            });
            return {
                selection: JSON.parse(actionValue || "[]"),
            };
        });
        onWillStart(async () => {
            await this.handleProps(this.props);
        });
        onWillUpdateProps(async (newProps) => {
            await this.handleProps(newProps);
        });
    }
    async handleProps(props) {
        if (props.m2oField) {
            const modelData = await this.fields.loadFields(props.model, {
                fieldNames: [props.m2oField],
            });
            this.state.searchModel = modelData[props.m2oField].relation;
            if (!this.state.searchModel) {
                throw new Error(`m2oField ${props.m2oField} is not a relation field`);
            }
        } else {
            this.state.searchModel = props.model;
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
