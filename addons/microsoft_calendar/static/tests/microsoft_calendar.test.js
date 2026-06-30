import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { defineActions, defineModels, fields, getService, models, mountWebClient, onRpc, serverState, switchView } from "@web/../tests/web_test_helpers";

class CalendarEvent extends models.Model {
    _name = "calendar.event";
    _records = [
        {
            id: 5,
            user_id: serverState.userId,
            partner_id: 4,
            name: "event 1",
            start: "2016-12-13 15:55:05",
            stop: "2016-12-15 18:55:05",
            allday: false,
            partner_ids: [4],
        },
        {
            id: 6,
            user_id: serverState.userId,
            partner_id: 5,
            name: "event 2",
            start: "2016-12-18 08:00:00",
            stop: "2016-12-18 09:00:00",
            allday: false,
            partner_ids: [4],
        },
    ];
    _views = {
        calendar: `
            <calendar js_class="attendee_calendar" date_start="start" date_stop="stop">
                <field name="name"/>
                <field name="partner_ids" write_model="calendar.filter" write_field="partner_id"/>
            </calendar>
        `,
        list: `<list sample="1"/>`
    };

    user_id = fields.Many2one({ relation: "users" });
    partner_id = fields.Many2one({ relation: "partner" });
    name = fields.Char();
    start = fields.Datetime();
    stop = fields.Datetime();
    allday = fields.Boolean();
    partner_ids = fields.One2many({ relation: "partner" });
}

class CalendarFilter extends models.Model {
    _records = [
        { id: 3, user_id: serverState.userId, partner_id: 4, partner_checked: true },
    ];

    user_id = fields.Many2one({ relation: "users" });
    partner_id = fields.Many2one({ relation: "partner" });
    partner_checked = fields.Boolean();
}

class Partner extends models.Model {
    _records = [
        { id: 4, name: "Partner 4", image_1920: "DDD" },
        { id: 5, name: "Partner 5", image_1920: "DDD" },
    ];

    name = fields.Char();
    image_1920 = fields.Binary();
}

class Users extends models.Model {
    _records = [
        { id: serverState.userId, name: "User 4", partner_id: 4 },
    ];

    name = fields.Char();
    partner_id = fields.Many2one({ relation: "partner" });
    image_1920 = fields.Binary();
}

defineModels([CalendarEvent, CalendarFilter, Partner, Users]);
defineMailModels();

onRpc("/calendar/check_credentials", async () => ({ microsoft_calendar: true }));
onRpc("/microsoft_calendar/sync_data", () => ({ status: "no_new_event_from_microsoft" }));
onRpc("check_synchronization_status", async () => ({ microsoft_calendar: "sync_active" }));
onRpc("get_attendee_detail", () => []);
onRpc("get_default_duration", () => 3.25);

beforeEach(() => {
    mockDate("2016-12-12 08:00:00");
});

test(`component is destroyed while sync microsoft calendar`, async () => {
    defineActions([
        {
            id: 1,
            name: "Partners",
            res_model: "calendar.event",
            type: "ir.actions.act_window",
            views: [[false, "list"], [false, "calendar"]],
        },
    ]);

    const deferred = Promise.withResolvers();
    onRpc("/microsoft_calendar/sync_data", async function () {
        expect.step("sync_data");
        return deferred.promise;
    });
    onRpc("calendar.event", "search_read", ({ method }) => {
        expect.step(method);
    });

    await mountWebClient();
    await getService("action").doAction(1);
    expect.verifySteps([]);

    await switchView("calendar");
    expect.verifySteps(["sync_data"]);

    await switchView("calendar");
    expect.verifySteps(["sync_data"]);

    deferred.resolve();
    await animationFrame();
    expect.verifySteps(["search_read"]);
});
