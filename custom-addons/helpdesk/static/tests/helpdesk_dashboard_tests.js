/** @odoo-module */

import {
    click,
    editInput,
    getFixture,
    getNodesTextContent,
    triggerEvent,
} from '@web/../tests/helpers/utils';
import {
    makeView,
    setupViewRegistries,
} from '@web/../tests/views/helpers';

let target;

QUnit.module('Views', {}, function () {

QUnit.module('Helpdesk Dashboard', {
    beforeEach: function() {
        this.makeViewParams = {
            type: 'kanban',
            resModel: 'partner',
            serverData: {
                models: {
                    partner: {
                        fields: {
                            foo: { string: "Foo", type: "char" },
                        },
                        records: [
                            { id: 1, foo: "yop" },
                            { id: 2, foo: "blip" },
                            { id: 3, foo: "gnap" },
                            { id: 4, foo: "blip" },
                        ]
                    },
                    'res.users': {
                        fields: {
                            helpdesk_target_closed: { string: "helpdesk target closed", type: "integer"},
                        },
                        records: [
                            { id: 7, helpdesk_target_closed: 12 },
                        ]
                    }
                },
                views: { },
            },
            arch: `
                <kanban class="o_kanban_test" js_class="helpdesk_team_kanban_view">
                    <templates><t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t></templates>
                </kanban>
            `,
        };
        this.dashboardData = {
            '7days': { count: 0, rating: 0, success: 0 },
            helpdesk_target_closed: 12,
            helpdesk_target_rating: 0,
            helpdesk_target_success: 0,
            my_all: { count: 0, hours: 0, failed: 0 },
            my_high: { count: 0, hours: 0, failed: 0 },
            my_urgent: { count: 0, hours: 0, failed: 0 },
            rating_enable: false,
            show_demo: false,
            success_rate_enable: false,
            today: { count: 0, rating: 0, success: 0 },
        };

        target = getFixture();
        setupViewRegistries();
    }
});

QUnit.test('dashboard basic rendering', async function(assert) {
    assert.expect(4);

    const dashboardData = this.dashboardData;
    await makeView({
        ...this.makeViewParams,
        mockRPC(route, args) {
            if (args.method === 'retrieve_dashboard') {
                assert.ok(true, "should call /retrieve_dashboard");
                return Promise.resolve(dashboardData);
            }
        },
    });

    assert.containsOnce(target, 'div.o_helpdesk_content', "should render the dashboard");
    assert.containsOnce(target, ".o_helpdesk_content > .o_helpdesk_banner",
        "dashboard should be sibling of renderer element");
    assert.deepEqual(
        getNodesTextContent(target.getElementsByClassName('o_target_to_set')),
        ['12'],
        "should have written correct targets",
    );
});

QUnit.test('edit the target', async function(assert) {
    assert.expect(7);

    const dashboardData = this.dashboardData;
    dashboardData.helpdesk_target_closed = 0;
    this.makeViewParams.serverData.models['res.users'].records[0].helpdesk_target_closed = 0
    await makeView({
        ...this.makeViewParams,
        mockRPC(route, args) {
            if (args.method === 'retrieve_dashboard') {
                // should be called twice: for the first rendering, and after the target update
                assert.ok(true, "should call /retrieve_dashboard");
                return Promise.resolve(dashboardData);
            } else if (args.model === 'res.users' && args.method === 'write') {
                assert.ok(true, "should modify helpdesk_target_closed");
                dashboardData.helpdesk_target_closed = args.args[1].helpdesk_target_closed;
                return Promise.resolve();
            }
        },
    });

    assert.deepEqual(
        getNodesTextContent(target.getElementsByClassName('o_target_to_set')).map(textNode => textNode.trim()),
        ["Click to set"],
        "should have correct targets",
    );

    // edit the target
    await click(target, '.o_target_to_set:nth-child(1)');
    assert.containsNone(target, '.o_target_to_set', 'The first one should be an input since the user clicked on it.');
    assert.containsOnce(target, '.o_helpdesk_banner .o_helpdesk_banner_table td > input', 'The input should be rendered instead of the span.');
    await editInput(target, '.o_helpdesk_banner .o_helpdesk_banner_table td > input', 1200);
    await triggerEvent(
        target,
        '.o_helpdesk_banner .o_helpdesk_banner_table td > input',
        'blur',
    );
    assert.containsNone(target, '.o_helpdesk_banner .o_helpdesk_banner_table td > input', 'The input should no longer be rendered since the user finished the edition by pressing Enter key.');

    assert.deepEqual(
        getNodesTextContent(target.getElementsByClassName('o_target_to_set')),
        ["1200"],
        "should have correct targets",
    );
});

QUnit.test('dashboard rendering with empty many2one', async function(assert) {
    assert.expect(2);

    // add an empty many2one
    const partnerModel = this.makeViewParams.serverData.models.partner;
    partnerModel.fields.partner_id = { string: "Partner", type: 'many2one', relation: 'partner' };
    partnerModel.records[0].partner_id = false;

    const dashboardData = this.dashboardData;
    await makeView({
        ...this.makeViewParams,
        mockRPC(route, args) {
            if (args.method === 'retrieve_dashboard') {
                assert.ok(true, "should call /retrieve_dashboard");
                return Promise.resolve(dashboardData);
            }
        },
    });

    assert.containsOnce(target, 'div.o_helpdesk_content', "should render the dashboard");
});

});
