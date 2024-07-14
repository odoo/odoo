/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Many2OneAvatarRankField extends Component {
    static template = "sale_timesheet_enterprise.Many2OneAvatarRankField";
    static props = {
        rank: { type: Number },
        id: { type: Number, optional: true },
        size: { type: String, optional: true },
        class: { type: String, optional: true },
    };
    static defaultProps = {
        id: 0,
        size: "small",
        class: "",
    };

    setup() {
        this.userService = useService("user");
    }

    get imgSrc() {
        return this.props.id === 0 ? "/hr/static/src/img/default_image.png" : `/web/image/hr.employee.public/${this.props.id}/avatar_128`;
    }

    get rankingClassBorder() {
        if (this.props.rank < 4) return "o-border-" + this.props.rank;
        return "border-primary";
    }

    get rankingClassBackground() {
        if (this.props.rank < 4) return "o-bg-" + this.props.rank;
        return "bg-primary";
    }
}
