import { Component, computed, t, useProps, xml } from "@odoo/owl";

/**
 * Renders a <widget> of a help view. Contrary to the widgets of other views,
 * there is no record: the widget component receives the props extracted from
 * the arch node only (so its `record` prop must be optional).
 */
export class HelpWidget extends Component {
    static template = xml`
        <div t-att-class="this.classNames()">
            <t t-component="this.widget().component" t-props="this.widgetProps()"/>
        </div>`;
    props = useProps({
        widgetInfo: t.object(),
        className: t.string().optional(),
    });

    widget = computed(() => this.props.widgetInfo.widget);

    classNames = computed(() => {
        const classNames = {
            o_widget: true,
            [`o_widget_${this.props.widgetInfo.name}`]: true,
            [this.props.className]: Boolean(this.props.className),
        };
        for (const cls of this.widget().additionalClasses || []) {
            classNames[cls] = true;
        }
        return classNames;
    });

    widgetProps = computed(() => {
        const { extractProps } = this.widget();
        return {
            readonly: true,
            ...(extractProps ? extractProps(this.props.widgetInfo, { readonly: true }) : {}),
        };
    });
}
