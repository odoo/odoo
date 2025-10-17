import { fields, models } from "@web/../tests/web_test_helpers";

export class TestTrackModel extends models.Model {
    _name = "test.track.model";

    char = fields.Char({ tracking: true });
    many2one = fields.Many2one({ relation: "test.track.other.model", tracking: true });
    boolean = fields.Boolean({ tracking: true });
    selection = fields.Selection({
        selection: [
            ["option_1", "Option 1"],
            ["option_2", "Option 2"],
            ["option_3", "Option 3"],
        ],
        tracking: true,
    });
    integer = fields.Integer({ tracking: true });
    float = fields.Float({ tracking: true });
}

export class TestTrackOtherModel extends models.Model {
    _name = "test.track.other.model";

    name = fields.Char();

    _records = [
        { id: 1, name: "Other 1" },
        { id: 2, name: "Other 2" },
    ];
}
