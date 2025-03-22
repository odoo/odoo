/** @odoo-module **/

import { click, getFixture, patchDate, makeDeferred, nextTick} from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { userService } from "@web/core/user_service";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";

const serviceRegistry = registry.category("services");

let target;
let serverData;
const uid = -1;

QUnit.module('Microsoft Calendar', {
    beforeEach: function () {
        patchDate(2016, 11, 12, 8, 0, 0);
        serverData = {
            models: {
                'calendar.event': {
                    fields: {
                        id: {string: "ID", type: "integer"},
                        user_id: {string: "user", type: "many2one", relation: 'user'},
                        partner_id: {string: "user", type: "many2one", relation: 'partner', related: 'user_id.partner_id'},
                        name: {string: "name", type: "char"},
                        start: {string: "start datetime", type: "datetime"},
                        stop: {string: "stop datetime", type: "datetime"},
                        partner_ids: {string: "attendees", type: "one2many", relation: 'partner'},
                    },
                },
                'appointment.type': {
                    fields: {},
                    records: [],
                },
                user: {
                    fields: {
                        id: {string: "ID", type: "integer"},
                        display_name: {string: "Displayed name", type: "char"},
                        partner_id: {string: "partner", type: "many2one", relation: 'partner'},
                        image_1920: {string: "image", type: "integer"},
                    },
                    records: [
                        {id: 4, display_name: "user 4", partner_id: 4},
                    ]
                },
                partner: {
                    fields: {
                        id: {string: "ID", type: "integer"},
                        display_name: {string: "Displayed name", type: "char"},
                        image_1920: {string: "image", type: "integer"},
                    },
                    records: [
                        {id: 4, display_name: "partner 4", image_1920: 'DDD'},
                        {id: 5, display_name: "partner 5", image_1920: 'DDD'},
                    ]
                },
                filter_partner: {
                    fields: {
                        id: {string: "ID", type: "integer"},
                        user_id: {string: "user", type: "many2one", relation: 'user'},
                        partner_id: {string: "partner", type: "many2one", relation: 'partner'},
                        partner_checked: {string: "checked", type: "boolean"},
                    },
                    records: [
                        {id: 3, user_id: uid, partner_id: 4, partner_checked: true}
                    ]
                },
            },
            views: {},
        };
        target = getFixture();
        setupViewRegistries();
        serviceRegistry.add(
            "user",
            {
                ...userService,
                start() {
                    const fakeUserService = userService.start(...arguments);
                    Object.defineProperty(fakeUserService, "userId", {
                        get: () => uid,
                    });
                    return fakeUserService;
                },
            },
            { force: true }
        );
    }
}, function () {

    QUnit.test("component is destroyed while sync microsoft calendar", async function (assert) {
        assert.expect(4);
        const def = makeDeferred();
        serverData.actions = {
            1: {
                id: 1,
                name: "Partners",
                res_model: "calendar.event",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "calendar"],
                ],
            },
        };

        serverData.views = {
            "calendar.event,false,calendar": `
                <calendar class="o_calendar_test" js_class="attendee_calendar" date_start="start" date_stop="stop">
                    <field name="name"/>
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>
                </calendar>`,
            "calendar.event,false,list": `<tree sample="1" />`,
            "calendar.event,false,search": `<search />`,
        };

        const webClient = await createWebClient({
            serverData,
            async mockRPC(route, args) {
                if (route === '/microsoft_calendar/sync_data') {
                    assert.step(route);
                    return def;
                } else if (route === '/web/dataset/call_kw/calendar.event/search_read') {
                    assert.step(route);
                } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                    return Promise.resolve([]);
                } else if (route === '/web/dataset/call_kw/res.users/has_group') {
                    return Promise.resolve(true);
                }
            },
        });

        await doAction(webClient, 1);

        click(target.querySelector(".o_cp_switch_buttons .o_calendar"));
        await nextTick();

        click(target.querySelector(".o_cp_switch_buttons .o_calendar"));
        await nextTick();

        def.resolve();
        await nextTick();

        assert.verifySteps([
            "/microsoft_calendar/sync_data",
            "/microsoft_calendar/sync_data",
            "/web/dataset/call_kw/calendar.event/search_read"
        ], "Correct RPC calls were made");
    });
});
