/** @odoo-module */
import { Widget } from "@web/views/widgets/widget";

export class WidgetStudio extends Widget {
    get widgetProps() {
        const widgetProps = super.widgetProps;
        delete widgetProps.studioXpath;
        delete widgetProps.hasEmptyPlaceholder;
        delete widgetProps.hasLabel;
        delete widgetProps.studioIsVisible;
        return widgetProps;
    }
}
