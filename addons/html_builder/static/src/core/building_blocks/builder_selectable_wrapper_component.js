import { useActionInfo, useSelectableLtrRtlComponent } from "@html_builder/core/utils";
import { Component, proxy, t, useEffect, useProps } from "@odoo/owl";

/**
 * @abstract
 */
export class BuilderSelectableWrapperComponent extends Component {
    static template;

    selectableProps = useProps({
        ltrRtlMapping: t.string().optional(),
        isLabelLinkedToContent: t.boolean().optional(),
    });

    setup() {
        const info = useActionInfo(this.props, { raw: true });
        this.itemPropsState = proxy({
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

        useEffect(() => {
            this.itemPropsState.className = this.props.className;
            this.itemPropsState.label = this.props.label;
            this.itemPropsState.title = this.props.title;
            this.itemPropsState.slots = this.props.slots;
        });

        if (this.selectableProps.ltrRtlMapping && !this.env.ignoreBuilderItem) {
            useSelectableLtrRtlComponent({
                ltrRtlMapping: this.selectableProps.ltrRtlMapping,
                isLabelLinkedToContent: this.selectableProps.isLabelLinkedToContent,
                getItemState: () => this.itemPropsState,
            });
        }
    }

    get forwardedProps() {
        return { ...this.props, ...this.itemPropsState };
    }
}
