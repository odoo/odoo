import { fields, models } from "@web/../tests/web_test_helpers";

export class BurndownChart extends models.ServerModel {
    _name = "project.task.burndown.chart.report";

    nb_tasks = fields.Integer({ string: "Number of Tasks" });

    _records = [
        { project_id: 1, stage_id: 1, is_closed: 'open', date: "2020-01-01", nb_tasks: 10 },
        { project_id: 1, stage_id: 2, is_closed: 'open', date: "2020-02-01", nb_tasks: 5 },
        { project_id: 1, stage_id: 3, is_closed: 'closed', date: "2020-03-01", nb_tasks: 2 },
    ];

    _views = {
        ["graph,false"]: `
            <graph type="line">
                <field name="date" string="Date" interval="month"/>
                <field name="stage_id"/>
                <field name="is_closed"/>
                <field name="nb_tasks" type="measure"/>
            </graph>`,
    };
}
