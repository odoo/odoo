/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class TimerToggleButton extends Component {
    setup() {
        this.orm = useService("orm");
    }

    get buttonClass() {
        const layout = this.props.record.data[this.props.name] ? 'danger' : 'primary';
        return `bg-${layout} text-bg-${layout}`;
    }

    get iconClass() {
        const icon = this.props.record.data[this.props.name] ? "stop" : "play";
        return `fa fa-${icon}-circle`;
    }

    get title() {
        return this.props.record.data[this.props.name] ? _t("Stop") : _t("Start");
    }

    async onClick(ev) {
        const action = this.props.record.data[this.props.name] ? "stop" : "start";
        await this.orm.call(
            this.props.record.resModel,
            `action_timer_${action}`,
            [[this.props.record.resId]],
            { context: this.props.context }
        );
        await this.props.record.model.load();
    }
}

TimerToggleButton.props = {
    ...standardFieldProps,
    context: { type: Object },
};
TimerToggleButton.template = "timer.ToggleButton";
