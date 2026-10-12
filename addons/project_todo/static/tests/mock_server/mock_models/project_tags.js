import { fields, models } from "@web/../tests/web_test_helpers";

export class ProjectTags extends models.Model {
    _name = "project.tags";

    name = fields.Char();
    color = fields.Integer();

    _records = [
        {
            id: 1,
            name: "Tag 1",
            color: 1,
        },
        {
            id: 2,
            name: "Tag 2",
            color: 5,
        },
        {
            id: 3,
            name: "Tag 3",
            color: 10,
        },
    ];
}
