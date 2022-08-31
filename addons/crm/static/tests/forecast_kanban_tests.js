/** @odoo-module */

import { FillTemporalService } from '@crm/js/forecast/fill_temporal_service';
import { ForecastKanbanView } from '../src/js/forecast/forecast_views';
import testUtils from 'web.test_utils';
import { mount, getFixture, patchWithCleanup, click, clickSave} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

let target;
let serverData;
let arch;
let unPatchDate;

QUnit.module('Crm Forecast Model Extension', {
    async beforeEach() {
        unPatchDate = testUtils.mock.patchDate(2021, 1, 10, 0, 0, 0);
        serverData = {
            views: {
                "crm.lead,false,search": `
                    <search>
                        <filter name="forecast" string="Forecast" context="{'forecast_filter':1}"/>
                        <filter name='groupby_date_deadline' context="{'group_by':'date_deadline'}"/>
                        <filter name='groupby_date_closed' context="{'group_by':'date_closed'}"/>
                    </search>`
            },
            models: {
                'crm.lead': {
                    fields: {
                        name: {string: 'Name', type: 'char'},
                        date_deadline: {string: "Expected closing", type: 'date'},
                        date_closed: {string: "Closed Date", type: 'datetime'},
                    },
                    records: [
                        {id: 1, name: 'Lead 1', date_deadline: '2021-01-01', date_closed: '2021-01-01 00:00:00'},
                        {id: 2, name: 'Lead 2', date_deadline: '2021-01-20', date_closed: '2021-01-20 00:00:00'},
                        {id: 3, name: 'Lead 3', date_deadline: '2021-02-01', date_closed: '2021-02-01 00:00:00'},
                        {id: 4, name: 'Lead 4', date_deadline: '2021-02-20', date_closed: '2021-02-20 00:00:00'},
                        {id: 5, name: 'Lead 5', date_deadline: '2021-03-01', date_closed: '2021-03-01 00:00:00'},
                        {id: 6, name: 'Lead 6', date_deadline: '2021-03-20', date_closed: '2021-03-20 00:00:00'},
                    ],
                },
            },
        };
        arch = `
            <kanban js_class="forecast_kanban">
                <field name="date_deadline"/>
                <field name="date_closed"/>
                <templates>
                    <t t-name="kanban-box">
                        <div><field name="name"/></div>
                    </t>
                </templates>
            </kanban>`;
        serviceRegistry.add("fillTemporalService", FillTemporalService);
        target = getFixture();
        setupViewRegistries();
    },
    async afterEach() {
        unPatchDate();
    },

}, function () {
    QUnit.test("filter out every records before the start of the current month with forecast_filter for a date field", async function (assert) {
        // the filter is used by the forecast model extension, and applies the forecast_filter context key,
        // which adds a domain constraint on the field marked in the other context key forecast_field
        assert.expect(7);

        const kanban = await makeView({
            type: "form",
            resModel: "crm.lead",
            serverData: serverData,
            arch: arch,
            groupBy: ['date_deadline'],
            context: {
                search_default_forecast: true,
                search_default_groupby_date_deadline: true,
                forecast_field: 'date_deadline',
            },
        });

        // the filter is active
        assert.containsN(kanban, '.o_kanban_group', 2, "There should be 2 columns");
        assert.containsN(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record', 2,
                        "1st column February should contain 2 record");
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 2,
                        "2nd column March should contain 2 records");

        // remove the filter
        await testUtils.dom.click($('.o_searchview_facet:contains("Forecast") .o_facet_remove'));

        assert.containsN(kanban, '.o_kanban_group', 3, "There should be 3 columns");
        assert.containsN(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record', 2,
                        "1st column January should contain 2 record");
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 2,
                        "2nd column February should contain 2 records");
        assert.containsN(kanban, '.o_kanban_group:nth-child(3) .o_kanban_record', 2,
                        "3nd column March should contain 2 records");
    });

    QUnit.test("filter out every records before the start of the current month with forecast_filter for a datetime field", async function (assert) {
        // same tests as for the date field
        assert.expect(7);

        const kanban = await makeView({
            type: "form",
            resModel: "crm.lead",
            serverData: serverData,
            arch: arch,
            groupBy: ['date_closed'],
            context: {
                search_default_forecast: true,
                search_default_groupby_date_closed: true,
                forecast_field: 'date_closed',
            },
        });

        // with the filter
        assert.containsN(kanban, '.o_kanban_group', 2, "There should be 2 columns");
        assert.containsN(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record', 2,
                        "1st column February should contain 2 record");
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 2,
                        "2nd column March should contain 2 records");

        // remove the filter
        await testUtils.dom.click($('.o_searchview_facet:contains("Forecast") .o_facet_remove'));

        assert.containsN(kanban, '.o_kanban_group', 3, "There should be 3 columns");
        assert.containsN(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record', 2,
                        "1st column January should contain 2 record");
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 2,
                        "2nd column February should contain 2 records");
        assert.containsN(kanban, '.o_kanban_group:nth-child(3) .o_kanban_record', 2,
                        "3nd column March should contain 2 records");
    });
});

QUnit.module('Crm Fill Temporal Service', {
    /**
     * Remark: -> the filter with the groupBy is needed for the model_extension to access the groupby
     * when created with testUtils.createView. Not needed in production.
     *         -> testKanbanView.groupBy is still needed to apply the groupby on the view
     */
    async beforeEach() {
        unPatchDate = testUtils.mock.patchDate(2021, 9, 10, 0, 0, 0);
        arch = `
            <kanban js_class="forecast_kanban">
                <field name="date_deadline"/>
                <templates>
                    <t t-name="kanban-box">
                        <div><field name="name"/></div>
                    </t>
                </templates>
            </kanban>`;
        serverData = {
            views: {
                "crm.lead,false,search": `
                    <search>
                        <filter name="forecast" string="Forecast" context="{'forecast_filter':1}"/>
                        <filter name='groupby_date_deadline' context="{'group_by':'date_deadline'}"/>
                    </search>`
            },
            models: {
                'crm.lead': {
                    fields: {
                        name: {string: 'Name', type: 'char'},
                        date_deadline: {string: "Expected Closing", type: 'date'},
                    },
                },
            },

        };
/*        services: { 'fillTemporalService': FillTemporalService },*/
        this.context = {
            search_default_forecast: true,
            search_default_groupby_date_deadline: true,
            forecast_field: 'date_deadline',
        };
        serviceRegistry.add("fillTemporalService", FillTemporalService);
        target = getFixture();
        setupViewRegistries();
    },
    async afterEach() {
        unPatchDate();
    },
}, function () {
    /**
     * Since mock_server does not support fill_temporal, 
     * we only check the domain and the context sent to the read_group, as well
     * as the end value of the FillTemporal Service after the read_group (which should have been updated in the model)
     */
    QUnit.test("Forecast on months, until the end of the year of the latest data", async function (assert) {
        assert.expect(3);

        serverData.models['crm.lead'].records = [
            {id: 1, name: 'Lead 1', date_deadline: '2021-01-01'},
            {id: 2, name: 'Lead 2', date_deadline: '2021-02-01'},
            {id: 3, name: 'Lead 3', date_deadline: '2021-11-01'},
            {id: 4, name: 'Lead 4', date_deadline: '2022-01-01'},
        ];
        const kanban = await makeView({
            type: "form",
            resModel: "crm.lead",
            serverData: serverData,
            arch: arch,
            groupBy: ['date_deadline'],
            context: this.context,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/crm.lead/web_read_group') {
                    assert.deepEqual(args.kwargs.context.fill_temporal, {
                        fill_from: "2021-10-01",
                        min_groups: 4,
                    });
                    assert.deepEqual(args.kwargs.domain, [
                        "&", "|",
                            ["date_deadline", "=", false], ["date_deadline", ">=", "2021-10-01"],
                        "|",
                            ["date_deadline", "=", false], ["date_deadline", "<", "2023-01-01"],
                    ]);
                }
            },
        });
        assert.strictEqual(kanban.call('fillTemporalService', 'getFillTemporalPeriod', {
            modelName: 'crm.lead',
            field: {
                name: 'date_deadline',
                type: 'date',
            },
            granularity: 'month',
        }).end.format('YYYY-MM-DD'), '2022-02-01');
    });

    /**
     * Since mock_server does not support fill_temporal, 
     * we only check the domain and the context sent to the read_group, as well
     * as the end value of the FillTemporal Service after the read_group (which should have been updated in the model)
     */
    QUnit.test("Forecast on years, until the end of the year of the latest data", async function (assert) {
        assert.expect(3);

        serverData.models['crm.lead'].records = [
            {id: 1, name: 'Lead 1', date_deadline: '2021-01-01'},
            {id: 2, name: 'Lead 2', date_deadline: '2022-02-01'},
            {id: 3, name: 'Lead 3', date_deadline: '2027-11-01'},
        ];

        serverData.views["crm.lead,false,search"] = 
            serverData.views["crm.lead,false,search"].replace(
                "'date_deadline'", "'date_deadline:year'"
            );
        const kanban = await makeView({
            type: "form",
            resModel: "crm.lead",
            serverData: serverData,
            arch: arch,
            groupBy: ['date_deadline:year'],
            context: this.context,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/crm.lead/web_read_group') {
                    assert.deepEqual(args.kwargs.context.fill_temporal, {
                        fill_from: "2021-01-01",
                        min_groups: 4,
                    });
                    assert.deepEqual(args.kwargs.domain, [
                        "&", "|",
                            ["date_deadline", "=", false], ["date_deadline", ">=", "2021-01-01"],
                        "|",
                            ["date_deadline", "=",  false], ["date_deadline", "<", "2025-01-01"],
                    ]);
                }
            },
        });
        assert.strictEqual(kanban.call('fillTemporalService', 'getFillTemporalPeriod', {
            modelName: 'crm.lead',
            field: {
                name: 'date_deadline',
                type: 'date',
            },
            granularity: 'year',
        }).end.format('YYYY-MM-DD'), '2023-01-01');
    });
});
