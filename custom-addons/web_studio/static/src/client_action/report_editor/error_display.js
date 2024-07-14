/** @odoo-module */
import { Component, onWillRender, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { humanReadableError } from "@web_studio/client_action/report_editor/utils";

export class ErrorDisplay extends Component {
    static template = "web_studio.ErrorDisplay";
    static props = { error: Object };

    setup() {
        this.state = useState({ showTrace: false });
        this.action = useService("action");
        onWillRender(() => {
            this.error = humanReadableError(this.props.error);
        });
    }
    openRecord(resModel, resId) {
        const action = {
            type: "ir.actions.act_window",
            target: "new",
            res_model: resModel,
            res_id: resId,
            views: [[false, "form"]],
            context: {
                studio: "0",
            },
        };
        this.action.doAction(action);
    }
    urlFor(model, resId, viewType = "form") {
        const searchParams = new URLSearchParams();
        Object.entries({ model, id: resId, view_type: viewType }).forEach(([k, v]) =>
            searchParams.set(k, v)
        );
        return `/web#${searchParams}`;
    }
}
