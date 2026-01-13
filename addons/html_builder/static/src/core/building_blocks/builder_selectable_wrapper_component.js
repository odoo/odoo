import { useActionInfo, useSelectableLtrRtlComponent } from "@html_builder/core/utils";
import { Component, onWillUpdateProps } from "@odoo/owl";
import { omit } from "@web/core/utils/objects";
import { useState } from "@web/owl2/utils";

export class BuilderSelectableWrapperComponent extends Component {
    static template = "";
    static props = {
        ltrRtlMapping: { type: String, optional: true },
        isLabelLinkedToContent: { type: Boolean, optional: true },
        // All props available to the wrapped component.
        "*": { optional: true },
    };

    setup() {
        const info = useActionInfo({ stringify: false });
        this.itemPropsState = useState({
            className: this.props.className,
            label: this.props.label,
            title: this.props.title,
            slots: this.props.slots,
            actionParam: info.actionParam,
            actionValue: info.actionValue,
            classAction: info.classAction,
            styleAction: info.styleAction,
            styleActionValue: info.styleActionValue,
            attributeAction: info.attributeAction,
            attributeActionValue: info.attributeActionValue,
            dataAttributeAction: info.dataAttributeAction,
            dataAttributeActionValue: info.dataAttributeActionValue,
        });

        onWillUpdateProps((nextProps) => {
            for (const prop of ["className", "label", "title", "slots"]) {
                if (prop in nextProps) {
                    this.itemPropsState[prop] = nextProps[prop];
                }
            }
        });

        if (this.props.ltrRtlMapping && !this.env.ignoreBuilderItem) {
            useSelectableLtrRtlComponent({
                ltrRtlMapping: this.props.ltrRtlMapping,
                isLabelLinkedToContent: this.props.isLabelLinkedToContent,
                getItemState: () => this.itemPropsState,
            });
        }
    }

    get forwardedProps() {
        return {
            ...omit(this.props, "ltrRtlMapping", "isLabelLinkedToContent"),
            ...this.itemPropsState,
        };
    }
}
