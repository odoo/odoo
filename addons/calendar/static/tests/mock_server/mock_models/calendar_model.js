import { fields, models, serverState } from "@web/../tests/web_test_helpers";

export class CalendarEvent extends models.Model {
    _name = "calendar.event";

    name = fields.Char();
    type_id = fields.Many2one({ string: "Event Type", relation: "event.type" });
    start_date = fields.Date();
    stop_date = fields.Date();
    start = fields.Datetime();
    stop = fields.Datetime();
    user_id = fields.Many2one({ relation: "res.users", default: serverState.userId });
    partner_id = fields.Many2one({ relation: "res.partner", default: 1 });
    partner_ids = fields.One2many({ relation: "res.partner", default: [[6, 0, [1]]] });
    color = fields.Integer({ related: "type_id.color" });

    check_access_rights() {
        return true;
    }

    _records = [
        {
            id: 1,
            name: "event 1",
            start: "2016-12-11 00:00:00",
            stop: "2016-12-11 00:00:00",
            user_id: serverState.userId,
            partner_id: 1,
            partner_ids: [1, 2, 3],
        },
        {
            id: 2,
            name: "event 2",
            start: "2016-12-12 10:55:05",
            stop: "2016-12-12 14:55:05",
            user_id: serverState.userId,
            partner_id: 1,
            partner_ids: [1, 2],
        },
        {
            id: 3,
            name: "event 3",
            start: "2016-12-12 15:55:05",
            stop: "2016-12-12 16:55:05",
            user_id: 4,
            partner_id: 4,
            partner_ids: [1],
        },
    ];

}

export class EventType extends models.Model {
    _name = "event.type";

    name = fields.Char();
    color = fields.Integer();

    check_access_rights() {
        return true;
    }

    _records = [
        { id: 1, name: "Event Type 1", color: 1 },
        { id: 2, name: "Event Type 2", color: 2 },
        { id: 3, name: "Event Type 3 (color 4)", color: 4 },
    ];
}

export class ResUsers extends models.Model {
    _name = "res.users";

    name = fields.Char();
    partner_id = fields.Many2one({ relation: "res.partner" });
    image = fields.Char();

    _records = [
        {
            "id": serverState.userId,
            "name": "user 1",
            "partner_id": 1
        },
        {
            "id": 4,
            "name": "user 4",
            "partner_id": 4
        }
    ];
}

export class ResPartner extends models.Model {
    _name = "res.partner";

    name = fields.Char();
    image = fields.Char();

    _records = [
        { id: 1, name: "partner 1", image: "AAA" },
        { id: 2, name: "partner 2", image: "BBB" },
        { id: 3, name: "partner 3", image: "CCC" },
        { id: 4, name: "partner 4", image: "DDD" },
    ];
}

export class CalendarFilters extends models.Model {
    _name = "calendar.filters";

    user_id = fields.Many2one({ relation: "res.users" });
    partner_id = fields.Many2one({ relation: "res.partner" });
    is_checked = fields.Boolean();

    _records = [
        {
            "id": 1,
            "user_id": serverState.userId,
            "partner_id": 1,
            "is_checked": true
        },
        {
            "id": 2,
            "user_id": serverState.userId,
            "partner_id": 2,
            "is_checked": true
        },
        {
            "id": 3,
            "user_id": 4,
            "partner_id": 3,
            "is_checked": false
        }
    ];
}
