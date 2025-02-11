import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { BuilderComponent } from "./builder_component";
import { BasicMany2Many } from "./basic_many2many";

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
        useModelEditState: Function,
        createAction: { type: String, optional: true },
        id: { type: String, optional: true },
        // currently always allowDelete
    };
    static defaultProps = {
        fields: [],
        domain: [],
        limit: 10,
    };
    static components = { BuilderComponent, BasicMany2Many };

    setup() {
        this.orm = useService("orm");
        this.fields = useService("field");
        // useBuilderComponent();
        this.state = useState({
            selection: undefined,
            searchModel: undefined,
        });
        onWillStart(async () => {
            await this.handleProps(this.props);
        });
        onWillUpdateProps(async (newProps) => {
            await this.handleProps(newProps);
        });
    }
    async handleProps(props) {
        const [record] = await this.orm.read(props.baseModel, [props.recordId], [props.m2oField]);
        const selectedRecordIds = record[props.m2oField];
        // TODO: handle no record
        const modelData = await this.fields.loadFields(props.baseModel, {
            fieldNames: [props.m2oField],
        });
        // TODO: simultaneously fly both RPCs
        this.state.searchModel = modelData[props.m2oField].relation;
        const temporary = this.props.useModelEditState({
            model: this.state.searchModel,
            recordId: props.recordId,
        });
        if (temporary.selection === undefined) {
            const storedSelection = await this.orm.read(this.state.searchModel, selectedRecordIds, [
                "display_name",
            ]);
            temporary.selection = [...storedSelection];
            for (const item of temporary.selection) {
                item.name = item.display_name;
            }
        }
        this.state.selection = temporary.selection;
    }
    setSelection(newSelection) {
        this.state.selection.length = 0;
        this.state.selection.push(...newSelection);
        // TODO participate in history
    }
}
