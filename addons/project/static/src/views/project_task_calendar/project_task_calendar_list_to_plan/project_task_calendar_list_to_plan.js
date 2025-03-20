import { Component } from "@odoo/owl";

export class ProjectTaskCalendarListToPlan extends Component {
    static template = "project.ProjectTaskCalendarListToPlan";
    static props = {
        model: Object,
        editRecord: Function,
    };

    get displayLoadMoreButton() {
        return this.props.model.tasksToPlan && this.props.model.tasksToPlan.records.length < this.props.model.tasksToPlan.length;
    }

    openRecord(task) {
        this.props.editRecord({ ...task, title: task.name });
    }

    async loadMoreTasksToPlan() {
        await this.props.model.loadMoreTasksToPlan();
    }
}
