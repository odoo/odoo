import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { BuilderComponent } from "./builder_component";
import { BasicMany2Many } from "./basic_many2many";
import { useDomState } from "@html_builder/core/building_blocks/utils";
import { useCachedModel } from "@html_builder/core/plugins/cached_model_utils";

export class ModelMany2Many extends Component {
    static template = "html_builder.ModelMany2Many";
    static props = {
        //...basicContainerBuilderComponentProps,
        baseModel: String,
        recordId: Number,
        m2oField: String,
        fields: { type: Array, element: String, optional: true },
        domain: { type: Array, optional: true },
        limit: { type: Number, optional: true },
        createAction: { type: String, optional: true },
        id: { type: String, optional: true },
        // currently always allowDelete
        applyTo: { type: String, optional: true },
    };
    static defaultProps = {
        fields: [],
        domain: [],
        limit: 10,
    };
    static components = { BuilderComponent, BasicMany2Many };

    setup() {
        this.fields = useService("field");
        this.cachedModel = useCachedModel();
        this.state = useState({
            searchModel: undefined,
        });
        this.modelEdit = undefined;
        this.selectionKey = undefined;
        this.domState = useDomState((el) => {
            if (!this.modelEdit) {
                return { selection: [] };
            }
            return {
                selection: this.modelEdit.get(this.selectionKey),
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
        const [record] = await this.cachedModel.ormRead(
            props.baseModel,
            [props.recordId],
            [props.m2oField]
        );
        const selectedRecordIds = record[props.m2oField];
        // TODO: handle no record
        const modelData = await this.fields.loadFields(props.baseModel, {
            fieldNames: [props.m2oField],
        });
        // TODO: simultaneously fly both RPCs
        this.state.searchModel = modelData[props.m2oField].relation;
        this.selectionKey = `${props.m2oField}Selection`;
        this.modelEdit = this.cachedModel.useModelEdit({
            model: this.props.baseModel,
            recordId: props.recordId,
        });
        if (!this.modelEdit.has(this.selectionKey)) {
            const storedSelection = await this.cachedModel.ormRead(
                this.state.searchModel,
                selectedRecordIds,
                ["display_name"]
            );
            for (const item of storedSelection) {
                item.name = item.display_name;
            }
            this.modelEdit.init(this.selectionKey, [...storedSelection]);
        }
        this.domState.selection = this.modelEdit.get(this.selectionKey);
    }
    setSelection(newSelection) {
        this.modelEdit.set(this.selectionKey, newSelection);
        this.env.editor.shared.history.addStep();
    }
}
