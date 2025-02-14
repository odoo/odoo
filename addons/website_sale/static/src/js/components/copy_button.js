import { CopyButton } from '@web/core/copy_button/copy_button';
import { registry } from '@web/core/registry';
import { standardWidgetProps } from "../standard_widget_props";

class CopyButtonWidget extends CopyButton {
    static props = {
        ...standardWidgetProps,
        ...CopyButton.props,
    };
}

export const copyButtonWidget = {
    component: CopyButtonWidget,
}

registry.category("view_widgets").add("copy_button", copyButtonWidget);
