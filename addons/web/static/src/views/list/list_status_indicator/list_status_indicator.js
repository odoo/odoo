import { t, useProps } from "@odoo/owl";
import {
    BaseStatusIndicatorSchema,
    FormStatusIndicator,
} from "@web/views/form/form_status_indicator/form_status_indicator";

export class ListStatusIndicator extends FormStatusIndicator {
    static template = "web.ListView.StatusIndicator";

    props = useProps({
        ...BaseStatusIndicatorSchema,
        onMouseDownDiscard: t.function().optional(),
    });

    get displayButtons() {
        return true;
    }
}
