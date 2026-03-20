import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatDate } from "@web/core/l10n/dates";

export class InternalResumeLineComponent extends Component {
    static template = "hr_skills.InternalResumeLineComponent";
    static props = { ...standardWidgetProps };

    setup(){
        super.setup();
        this.orm = useService("orm");
        onWillStart(async () => {
            this.internalResumeLines = await this.getInternalResumeLines(
                this.props.record.resId,
                this.props.record.resModel
            )
        })
        onWillUpdateProps(async (nextProps) => {
            this.internalResumeLines = await this.getInternalResumeLines(
                nextProps.record.resId,
                nextProps.record.resModel
            )
        })
    }

    async getInternalResumeLines(resId, resModel){
        const internalResumeLines = await this.orm.call(
            "hr.employee",
            "get_internal_resume_lines",
            [resId, resModel]
        );
        return internalResumeLines;
    }

    get companyId(){
        return this.props.record.data.company_id.display_name;
    }

    get haveResumeLines(){
        return this.props.record.data.resume_line_ids.records.length || this.internalResumeLines.length;
    }

    formatDate(date) {
        const formattedDate = luxon.DateTime.fromISO(date);
        return formatDate(formattedDate);
    }
}

export const internalResumeLinesComponent = {
    component: InternalResumeLineComponent,
    fieldDependencies: [
        { name: "company_id", type: "many2one" },
        { name: "resume_line_ids", type: "one2many"}
    ],
};

registry.category("view_widgets").add("internal_resume_lines", internalResumeLinesComponent);
