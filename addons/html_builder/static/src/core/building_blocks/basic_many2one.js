import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { basicContainerBuilderComponentProps } from "../utils";
import { useCachedModel } from "@html_builder/core/cached_model_utils";
import { SelectMany2X } from "./select_many2x";

export class BasicMany2One extends Component {
    static template = "html_builder.BasicMany2One";
    static props = {
        ...basicContainerBuilderComponentProps,
        model: String,
        fields: { type: Array, element: String, optional: true },
        domain: { type: Array, optional: true },
        limit: { type: Number, optional: true },
        selected: { type: Object, optional: true },
        select: Function,
        unselect: { type: Function, optional: true },
        defaultMessage: { type: String, optional: true },
        create: { type: Function, optional: true },
    };
    static components = { SelectMany2X };

    setup() {
        this.cachedModel = useCachedModel();
        onWillStart(async () => {
            await this.handleProps(this.props);
        });
        onWillUpdateProps(async (newProps) => {
            await this.handleProps(newProps);
        });
    }
    async handleProps(props) {
        if (props.selected && !("display_name" in props.selected && "name" in props.selected)) {
            Object.assign(
                props.selected,
                (
                    await this.cachedModel.ormRead(
                        this.props.model,
                        [props.selected.id],
                        ["display_name", "name"]
                    )
                )[0]
            );
        }
    }
}
