import { Widget } from "@web/views/widgets/widget";
import { studioIsVisible, useStudioRef } from "@web_studio/client_action/view_editor/editors/utils";

export class WidgetStudio extends Widget {
    static template = "web_studio.Widget";
    setup() {
        super.setup();
        useStudioRef("rootRef", this.onClick);
    }
    get classNames() {
        const classNames = super.classNames;
        classNames["o_web_studio_show_invisible"] = !studioIsVisible(this.props);
        classNames["o-web-studio-editor--element-clickable"] = !!this.props.studioXpath;
        return classNames;
    }
    get widgetProps() {
        const widgetProps = super.widgetProps;
        delete widgetProps.studioXpath;
        delete widgetProps.hasEmptyPlaceholder;
        delete widgetProps.hasLabel;
        delete widgetProps.studioIsVisible;
        return widgetProps;
    }
    onClick(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.env.config.onNodeClicked(this.props.studioXpath);
    }
}
