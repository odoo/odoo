import { Component, proxy, signal } from "@odoo/owl";
import { formatFloatTime } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { useSubEnv, useEnv } from "@web/owl2/utils";
import { ListRenderer } from "@web/views/list/list_renderer";

export class OvertimeDetailsPopover extends Component {
    static template = "hr_attendance.OvertimeDetailsPopover";
    static components = { ListRenderer };
    static props = { close: Function, list: Object, archInfo: Object, config: Object };

    setup() {
        useSubEnv({
            config: this.props.config,
        });
    }

    get rendererProps() {
        return {
            activeActions: {},
            archInfo: this.props.archInfo,
            cycleOnTab: false,
            list: this.props.list,
            openRecord: () => {},
            readonly: true,
        };
    }
}

export class OvertimeDetails extends Component {
    static template = "hr_attendance.OvertimeDetails";
    static props = {
        ...standardFieldProps,
        archInfo: { type: Object, optional: true },
    };

    static fieldDependencies = [
        {
            name: "linked_overtime_ids",
            type: "one2many",
            relation: "hr.attendance.overtime.line",
        },
    ];

    setup() {
        this.orm = useService("orm");
        this.popover = usePopover(OvertimeDetailsPopover);
        this.widget = signal.ref(HTMLDivElement);
        this.state = proxy({ totalDuration: 0 });
        this.env = useEnv();
    }

    get formattedTotal() {
        return formatFloatTime(this.props.record.data.overtime_hours);
    }

    onClickDetails() {
        const list = this.props.record.data.linked_overtime_ids;
        this.popover.open(this.widget(), {
            list,
            archInfo: this.props.archInfo,
            config: this.env.config,
        });
    }
}

export const overtimeDetails = {
    component: OvertimeDetails,
    useSubView: true,
    extractProps: ({ views }) => ({
        archInfo: views.list,
    }),
};

registry.category("fields").add("overtime_details", overtimeDetails);
