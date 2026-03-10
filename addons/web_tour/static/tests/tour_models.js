import { models, fields } from "@web/../tests/web_test_helpers";

export class TourStep extends models.Model {
    _name = "web_tour.tour.step";
    trigger = fields.Char();
    content = fields.Char();
    run = fields.Char();
    tour_id = fields.Many2one({ relation: "web_tour.tour" });
}

export class Tour extends models.Model {
    _name = "web_tour.tour";
    name = fields.Char();
    step_ids = fields.One2many({ relation: "web_tour.tour.step", relation_field: "tour_id" });
    url = fields.Char({ string: "Starting URL" });
    get_tour_json_by_name(name) {
        const tourModel = this.env["web_tour.tour"];
        const stepModel = this.env["web_tour.tour.step"];
        const tourIds = tourModel.search([["name", "=", name]]);
        if (!tourIds.length) {
            return false;
        }
        const tourData = tourModel.read(tourIds, ["name", "url"])[0];
        const stepIds = stepModel.search([["tour_id", "=", tourData.id]]);
        const steps = stepModel.read(stepIds, ["trigger", "content", "run"]);
        tourData.steps = steps;
        return tourData;
    }
}
