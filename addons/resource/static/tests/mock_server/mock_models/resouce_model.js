import { fields, models } from "@web/../tests/web_test_helpers";

export class user extends models.Model {
    _name = "res.users";

    name = fields.Char();

    has_group() {
        return true;
    }
}

export class resouce extends models.Model {
    _name = "resouce.resouce";

    id = fields.Integer();
    name = fields.Char();
    resource_type = fields.Selection({
        selection: [
            ["user", "Human"],
            ["material", "material"],
        ],
        default: "user",
    });

    _records = [{
            id: 1,
            name: "admin",
            resource_type: 'user',
        }, {
            id: 2,
            name: "crane",
            resource_type: 'material',
        },
    ];
}
