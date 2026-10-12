import { Component, useProps, t, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Alert extends Component {
    static template = xml`
        <div t-attf-class="alert pos-navbar-height fixed-top py-3 px-1 mt-2 lh-sm alert-{{this.props.type}} fade show d-flex align-items-center justify-content-center rounded {{this.ui.isSmall ? 'w-100': 'w-50 fs-5 m-auto'}}" role="alert">
            <strong class="flex-grow-1 text-center" t-out="this.props.message" />
            <button t-if="this.props.closable" t-on-click="this.props.onClose" class="btn btn-lg btn-close position-absolute end-0 me-2"/>
        </div>
    `;
    props = useProps({
        message: t.string(),
        type: t.selection(["info", "warning", "danger", "success"]).optional("info"),
        onClose: t.function(),
        closable: t.boolean().optional(false),
    });
    setup() {
        super.setup(...arguments);
        this.ui = useService("ui");
    }
}
