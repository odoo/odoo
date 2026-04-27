import { beforeEach, describe, destroy, expect, test } from "@odoo/hoot";
import { queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame, Deferred, mockTimeZone } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    findComponent,
    mockService,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { MapController } from "@web_map/map_view/map_controller";
import { MapModel } from "@web_map/map_view/map_model";
import { MapRenderer } from "@web_map/map_view/map_renderer";

const MAP_BOX_TOKEN = "token";

function getMapController(view) {
    return findComponent(view, (c) => c instanceof MapController);
}

function getMapRenderer(view) {
    return findComponent(view, (c) => c instanceof MapRenderer);
}

const TEST_RECORDS = {
    task: {
        oneRecord: [{ id: 1, name: "Foo", partner_id: 1 }],
        twoRecordsFieldDateTime: [
            { id: 1, name: "Foo", scheduled_date: false, partner_id: 1 },
            {
                id: 2,
                name: "Bar",
                scheduled_date: "2022-02-07 21:09:31",
                partner_id: 2,
            },
        ],
        twoRecords: [
            { id: 1, name: "FooProject", sequence: 1, partner_id: 1 },
            { id: 2, name: "BarProject", sequence: 2, partner_id: 2 },
        ],
        threeRecords: [
            {
                id: 1,
                name: "FooProject",
                sequence: 1,
                partner_id: 1,
                partner_ids: [1, 2],
            },
            {
                id: 2,
                name: "BarProject",
                sequence: 2,
                partner_id: 2,
                partner_ids: [1],
            },
            {
                id: 3,
                name: "FooBarProject",
                sequence: 3,
                partner_id: 1,
                partner_ids: [1],
            },
        ],
        twoRecordOnePartner: [
            { id: 1, name: "FooProject", partner_id: 1 },
            { id: 2, name: "BarProject", partner_id: 1 },
        ],
        recordWithouthPartner: [{ id: 1, name: "Foo", partner_id: false }],
        anotherPartnerId: [{ id: 1, name: "FooProject", another_partner_id: 1 }],
    },
    partner: {
        coordinatesNoAddress: [
            {
                id: 1,
                name: "Foo",
                partner_latitude: 10.0,
                partner_longitude: 10.5,
            },
        ],
        oneLocatedRecord: [
            {
                id: 1,
                name: "Foo",
                partner_latitude: 10.0,
                partner_longitude: 10.5,
                contact_address_complete: "Chaussée de Namur 40, 1367, Ramillies",
                sequence: 1,
            },
        ],
        wrongCoordinatesNoAddress: [
            {
                id: 1,
                name: "Foo",
                partner_latitude: 10000.0,
                partner_longitude: 100000.5,
            },
        ],
        noCoordinatesGoodAddress: [
            {
                id: 1,
                name: "Foo",
                partner_latitude: 0,
                partner_longitude: 0,
                contact_address_complete: "Chaussée de Namur 40, 1367, Ramillies",
            },
        ],
        twoRecordsAddressNoCoordinates: [
            {
                id: 2,
                name: "Foo",
                contact_address_complete: "Chaussée de Namur 40, 1367, Ramillies",
                sequence: 3,
            },
            {
                id: 1,
                name: "Bar",
                contact_address_complete: "Chaussée de Louvain 94, 5310 Éghezée",
                sequence: 1,
            },
        ],
        twoRecordsAddressCoordinates: [
            {
                id: 2,
                name: "Foo",
                partner_latitude: 10.0,
                partner_longitude: 10.5,
                contact_address_complete: "Chaussée de Namur 40, 1367, Ramillies",
                sequence: 3,
            },
            {
                id: 1,
                name: "Bar",
                partner_latitude: 10.0,
                partner_longitude: 10.5,
                contact_address_complete: "Chaussée de Louvain 94, 5310 Éghezée",
                sequence: 1,
            },
        ],
        twoRecordsOneUnlocated: [
            {
                id: 1,
                name: "Foo",
                contact_address_complete: "Chaussée de Namur 40, 1367, Ramillies",
                sequence: 3,
            },
            {
                id: 2,
                name: "Bar",
            },
        ],
        threeRecords: [
            {
                id: 1,
                name: "Foo",
                partner_latitude: 10.0,
                partner_longitude: 10.5,
                contact_address_complete: "Chaussée de Namur 40, 1367, Ramillies",
                sequence: 1,
                user_id: 1,
            },
            {
                id: 2,
                name: "Bar",
                partner_latitude: 11.0,
                partner_longitude: 11.5,
                contact_address_complete: "Chaussée de Wavre 50, 1367, Ramillies",
                sequence: 2,
                user_id: 2,
            },
            {
                id: 3,
                name: "Baz",
                partner_latitude: 12.0,
                partner_longitude: 12.5,
                contact_address_complete: "Chaussée de Louvain 94, 5310 Éghezée",
                sequence: 3,
                user_id: false,
            },
        ],
        unlocatedRecords: [{ id: 1, name: "Foo" }],
        noCoordinatesWrongAddress: [
            {
                id: 1,
                name: "Foo",
                contact_address_complete: "Cfezfezfefes",
            },
        ],
    },
};

class Task extends models.Model {
    _name = "project.task";

    name = fields.Char();
    scheduled_date = fields.Datetime({ string: "Schedule date" });
    task_status = fields.Selection({
        string: "Status",
        selection: [
            ["abc", "ABC"],
            ["def", "DEF"],
            ["ghi", "GHI"],
        ],
    });
    sequence = fields.Integer();
    partner_id = fields.Many2one({
        string: "partner",
        relation: "res.partner",
    });
    another_partner_id = fields.Many2one({
        string: "another relation",
        relation: "res.partner",
    });
    partner_ids = fields.One2many({
        string: "Partners",
        comodel_name: "res.partner",
        relation: "res.partner",
        relation_field: "task_id",
    });

    _records = [{ id: 1, name: "project", partner_id: 1 }];
}

class Users extends models.Model {
    _name = "res.users";

    name = fields.Char();
    _records = [
        { id: 1, name: "Mitchell Admin" },
        { id: 2, name: "Marc Demo" },
    ];
}

class Partner extends models.Model {
    _name = "res.partner";

    name = fields.Char({ string: "Customer" });
    partner_latitude = fields.Float({ string: "Latitude" });
    partner_longitude = fields.Float({ string: "Longitude" });
    contact_address_complete = fields.Char({ string: "Address" });
    task_ids = fields.One2many({
        string: "Task",
        relation: "project.task",
        relation_field: "partner_id",
    });
    sequence = fields.Integer();
    user_id = fields.Many2one({
        string: "Salesperson",
        relation: "res.users",
    });

    _records = [
        {
            id: 1,
            name: "Foo",
            partner_latitude: 10.0,
            partner_longitude: 10.5,
            contact_address_complete: "Chaussée de Namur 40, 1367, Ramillies",
            sequence: 1,
            user_id: 1,
        },
        {
            id: 2,
            name: "Foo",
            partner_latitude: 10.0,
            partner_longitude: 10.5,
            contact_address_complete: "Chaussée de Namur 40, 1367, Ramillies",
            sequence: 3,
            user_id: 2,
        },
        {
            id: 3,
            name: "Bar",
            partner_latitude: 11.0,
            partner_longitude: 11.5,
            contact_address_complete: "Chaussée de Wavre 50, 1367, Ramillies",
            sequence: 4,
            user_id: false,
        },
    ];

    update_latitude_longitude() {
        return true;
    }
}

defineModels([Task, Users, Partner]);

beforeEach(() => {
    patchWithCleanup(MapModel, {
        // set delay to 0 as _fetchCoordinatesFromAddressOSM is mocked
        COORDINATE_FETCH_DELAY: 0,
    });
    patchWithCleanup(MapModel.prototype, {
        async _fetchCoordinatesFromAddressMB(metaData, data, record) {
            if (metaData.mapBoxToken !== MAP_BOX_TOKEN) {
                return Promise.reject({ status: 401 });
            }
            const coordinates = [];
            coordinates[0] = "10.0";
            coordinates[1] = "10.5";
            const geometry = { coordinates };
            const features = [];
            features[0] = { geometry };
            const successResponse = { features };
            const failResponse = { features: [] };
            switch (record.contact_address_complete) {
                case "Cfezfezfefes":
                    return failResponse;
                case "":
                    return failResponse;
            }
            return successResponse;
        },
        async _fetchCoordinatesFromAddressOSM(metaData, data, record) {
            const coordinates = [];
            coordinates[0] = { lat: "10.0", lon: "10.5" };
            switch (record.contact_address_complete) {
                case "Cfezfezfefes":
                    return [];
                case "":
                    return [];
            }
            return coordinates;
        },
        async _fetchRoute(metaData, data) {
            if (metaData.mapBoxToken !== MAP_BOX_TOKEN) {
                return Promise.reject({ status: 401 });
            }
            const legs = [];
            for (let i = 1; i < data.records.length; i++) {
                const coordinates = [];
                coordinates[0] = [10, 10.5];
                coordinates[1] = [10, 10.6];
                const geometry = { coordinates };
                const steps = [];
                steps[0] = { geometry };
                legs.push({ steps: steps });
            }
            const routes = [];
            routes[0] = { legs };
            return { routes };
        },
        _notifyFetchedCoordinate(metaData, data) {
            // do not notify in tests as coords fetching is " synchronous "
        },
        _openStreetMapAPI(metaData, data) {
            // return promise to wait for it
            return this._openStreetMapAPIAsync(metaData, data);
        },
    });
});

describe.tags("desktop");
describe("map_view_desktop", () => {
    //--------------------------------------------------------------------------
    // Testing data fetching
    //--------------------------------------------------------------------------

    /**
     * data: no record
     * Should have no record
     * Should have no marker
     * Should have no route
     */
    test("Create a view with no record", async () => {
        expect.assertions(6);
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });
        Task._records = [];
        onRpc("project.task", "web_search_read", ({ kwargs }) => {
            const specification = kwargs.specification;
            expect(specification.partner_id).toEqual({
                fields: {
                    contact_address_complete: {},
                    display_name: {},
                    partner_latitude: {},
                    partner_longitude: {},
                },
            });
            expect(specification.name).toEqual({});
        });
        onRpc("res.partner", "search_read", () => {
            throw new Error("Should not search_read the partners if there are no partner");
        });
        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `
                    <map res_partner="partner_id" routing="1">
                        <field name="name" string="Project"/>
                        <field name="partner_ids" string="Project"/>
                    </map>
                `,
        });
        expect("a.btn.btn-primary").toHaveAttribute(
            "href",
            "https://www.google.com/maps/dir/?api=1",
            {
                message: "The link's URL should not contain any coordinates",
            }
        );
        expect("div.leaflet-marker-icon").toHaveCount(0, {
            message: "No marker should be on a the map.",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(0);
    });

    /**
     * data: one record that has no partner linked to it
     * The record shouldn't be kept and displayed in the list of records
     * should have no marker
     * Should have no route
     */
    test("Create a view with one record that has no partner", async () => {
        Task._records = TEST_RECORDS.task.recordWithouthPartner;
        Partner._records = [];

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect("div.leaflet-marker-icon").toHaveCount(0, {
            message: "No marker should be on a the map.",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(0);
    });

    /**
     * data: one record that has a partner which has coordinates but no address
     * One record
     * One marker
     * no route
     */
    test("Create a view with one record and a partner located by coordinates", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.coordinatesNoAddress;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect("div.leaflet-marker-icon").toHaveCount(1, {
            message: "There should be one marker on the map",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(1);
    });

    /**
     * data: one record linked to one partner with no address and wrong coordinates
     * api: MapBox
     * record shouldn't be kept and displayed in the list
     * no route
     * no marker
     */
    test("Create view with one record linked to a partner with wrong coordinates with MB", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.wrongCoordinatesNoAddress;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect("div.leaflet-marker-icon").toHaveCount(0, {
            message: "There should be np marker on the map",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(0);
    });

    /**
     * data: one record linked to one partner with no address and wrong coordinates
     * api: OpenStreet Map
     * record should be kept
     * no route
     * no marker
     */
    test("Create view with one record linked to a partner with wrong coordinates with OSM", async () => {
        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.wrongCoordinatesNoAddress;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect("div.leaflet-marker-icon").toHaveCount(0, {
            message: "There should be no marker on the map",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(0);
    });
    /**
     * data: one record linked to one partner with no coordinates and good address
     * api: OpenStreet Map
     * caching RPC called, assert good args
     * one record
     * no route
     */
    test("Create View with one record linked to a partner with no coordinates and right address OSM", async () => {
        expect.assertions(5);

        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.noCoordinatesGoodAddress;

        onRpc("res.partner", "update_latitude_longitude", ({ args }) => {
            expect(args[0]).toHaveLength(1, {
                message: "There should be one record needing caching",
            });
            expect(args[0][0].id).toBe(1, { message: "The records's id should be 1" });
            return {};
        });
        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(1);
        expect("div.leaflet-marker-icon").toHaveCount(1, {
            message: "There should be one marker on the map",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
    });

    /**
     * data: one record linked to one partner with no coordinates and good address
     * api: MapBox
     * caching RPC called, assert good args
     * one record
     * no route
     */
    test("Create View with one record linked to a partner with no coordinates and right address MB", async () => {
        expect.assertions(5);

        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.noCoordinatesGoodAddress;
        onRpc("res.partner", "update_latitude_longitude", ({ args }) => {
            expect(args[0]).toHaveLength(1, {
                message: "There should be one record needing caching",
            });
            expect(args[0][0].id).toBe(1, { message: "The records's id should be 1" });
            return {};
        });

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(1);
        expect("div.leaflet-marker-icon").toHaveCount(1, {
            message: "There should be one marker on the map",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
    });

    /**
     * data: one record linked to a partner with no coordinates and no address
     * api: MapBox
     * 1 record
     * no route
     * no marker
     */
    test("Create view with no located record", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.unlocatedRecords;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(0);
        expect("div.leaflet-marker-icon").toHaveCount(0, {
            message: "No marker should be on a the map.",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
    });

    /**
     * data: one record linked to a partner with no coordinates and no address
     * api: OSM
     * one record
     * no route
     * no marker
     */
    test("Create view with no located record OSM", async () => {
        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.unlocatedRecords;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(0);
        expect("div.leaflet-marker-icon").toHaveCount(0, {
            message: "No marker should be on a the map.",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
    });

    /**
     * data: one record linked to a partner with no coordinates and wrong address
     * api: OSM
     * one record
     * no route
     * no marker
     */
    test("Create view with no badly located record OSM", async () => {
        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.noCoordinatesWrongAddress;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(0);
        expect("div.leaflet-marker-icon").toHaveCount(0, {
            message: "No marker should be on a the map.",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
    });

    /**
     * data: one record linked to a partner with no coordinates and wrong address
     * api: mapbox
     * one record
     * no route
     * no marker
     */

    test("Create view with no badly located record MB", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.noCoordinatesWrongAddress;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(0);
        expect("div.leaflet-marker-icon").toHaveCount(0, {
            message: "No marker should be on a the map.",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
    });

    /**
     * data: 2 records linked to the same partner
     * 2 records
     * 2 markers
     * no route
     * same partner object
     * 1 caching request
     */
    test("Create a view with two located records same partner", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.twoRecordOnePartner;
        Partner._records = TEST_RECORDS.partner.oneLocatedRecord;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(2);
        expect("div.leaflet-marker-icon .o-map-renderer--marker-badge").toHaveText("2", {
            message: "There should be a marker for two records",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(1);
    });

    /**
     * data: 2 records linked to differnet partners
     * 2 records
     * 1 route
     * different partner object.
     * 2 caching
     */
    test("Create a view with two located records different partner", async () => {
        expect.assertions(5);
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;
        onRpc("res.partner", "update_latitude_longitude", ({ args }) => {
            expect(args[0]).toHaveLength(2, {
                message: "Should have 2 record needing caching",
            });
            return {};
        });

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        const controller = getMapController(view);
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(2);
        expect("div.leaflet-marker-icon .o-map-renderer--marker-badge").toHaveText("2", {
            message: "There should be a marker for two records",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(1);
        expect(controller.model.data.records[0].partner).not.toBe(
            controller.model.data.records[1].partner,
            { message: "The records should have the same partner object as a property" }
        );
    });

    /**
     * data: 2 valid res.partner records
     * test the case where the model is res.partner and the "res.partner" field is the id
     * should have 2 records,
     * 2 markers
     * no route
     */
    test("Create a view with res.partner", async () => {
        expect.assertions(4);
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Partner._records = [
            {
                id: 2,
                name: "Foo",
                contact_address_complete: "Chaussée de Namur 40, 1367, Ramillies",
                sequence: 3,
            },
            {
                id: 1,
                name: "FooBar",
                contact_address_complete: "Chaussée de Louvain 94, 5310 Éghezée",
                sequence: 1,
            },
        ];
        onRpc("res.partner", "web_search_read", ({ kwargs }) => {
            expect(kwargs.specification).toEqual({
                contact_address_complete: {},
                display_name: {},
                id: {},
                partner_latitude: {},
                partner_longitude: {},
            });
        });
        await mountView({
            type: "map",
            resModel: "res.partner",
            arch: `<map res_partner="id" />`,
        });
        expect(
            ".o-map-renderer--pin-list-container .o-map-renderer--pin-list-details li"
        ).toHaveCount(2);
        expect("div.leaflet-marker-icon .o-map-renderer--marker-badge").toHaveText("2", {
            message: "There should be a marker for two records",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
    });

    /**
     * Data: 3 partner records with user_id used as groupBy
     * Test if the map view displays the many2one field's name as the group name
     */
    test("Create a view with many2one groupBy and res.partner model", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Partner._records = TEST_RECORDS.partner.threeRecords;

        await mountView({
            type: "map",
            resModel: "res.partner",
            arch: `<map res_partner="id" />`,
            groupBy: ["user_id"],
        });

        expect(".o-map-renderer--pin-list-group-header").toHaveCount(3, {
            message: "Should have 3 groups",
        });

        expect(queryAllTexts(".o-map-renderer--pin-list-group-header")).toEqual(
            ["Mitchell Admin", "Marc Demo", "None"],
            {
                message: "Should have correct group headers",
            }
        );

        expect(".o-map-renderer--pin-list-details").toHaveCount(3, {
            message: "Should have 3 group detail sections",
        });

        expect(".o-map-renderer--pin-list-details li").toHaveCount(3, {
            message: "Should have 3 total records across all groups",
        });
    });

    /**
     * data: 3 records linked to one located partner and one unlocated
     * test if only the 2 located records are displayed
     */
    test("Create a view with 2 located records and 1 unlocated", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.threeRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsOneUnlocated;

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        const controller = getMapController(view);
        expect(controller.model.data.records.length).toBe(3);
        expect(controller.model.data.records[0].partner.id).toBe(1, {
            message: "The partner's id should be 1",
        });
        expect(controller.model.data.records[1].partner.id).toBe(2, {
            message: "The partner's id should be 2",
        });
        expect(controller.model.data.records[2].partner.id).toBe(1, {
            message: "The partner's id should be 1",
        });
    });

    test("Change load limit", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.threeRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressCoordinates;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" limit="2" />`,
        });
        expect(`.o_pager_counter .o_pager_value`).toHaveText("1-2");
        expect(`.o_pager_counter span.o_pager_limit`).toHaveText("3");
    });

    //--------------------------------------------------------------------------
    // Renderer testing
    //--------------------------------------------------------------------------

    test("Google Maps redirection", async () => {
        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id"></map>`,
        });

        expect("a.btn.btn-primary").toHaveAttribute(
            "href",
            "https://www.google.com/maps/dir/?api=1&waypoints=Chauss%C3%A9e%20de%20Louvain%2094%2C%205310%20%C3%89ghez%C3%A9e|Chauss%C3%A9e%20de%20Namur%2040%2C%201367%2C%20Ramillies",
            { message: "The link's URL should contain the address" }
        );

        await contains(".leaflet-marker-icon").click();
        expect("div.leaflet-popup a.btn.btn-primary").toHaveAttribute(
            "href",
            "https://www.google.com/maps/dir/?api=1&destination=Chauss%C3%A9e%20de%20Namur%2040%2C%201367%2C%20Ramillies",
            { message: "The URL of the link should contain the address" }
        );
    });

    test("Google Maps redirection (with routing = true)", async () => {
        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1"></map>`,
        });

        expect("a.btn.btn-primary").toHaveAttribute(
            "href",
            "https://www.google.com/maps/dir/?api=1&destination=Chauss%C3%A9e%20de%20Namur%2040%2C%201367%2C%20Ramillies&waypoints=Chauss%C3%A9e%20de%20Louvain%2094%2C%205310%20%C3%89ghez%C3%A9e",
            { message: "The link's URL should contain the address" }
        );

        await contains(".leaflet-marker-icon").click();
        expect("div.leaflet-popup a.btn.btn-primary").toHaveAttribute(
            "href",
            "https://www.google.com/maps/dir/?api=1&destination=Chauss%C3%A9e%20de%20Namur%2040%2C%201367%2C%20Ramillies",
            { message: "The URL of the link should contain the address" }
        );
    });

    test("Unicity of coordinates in Google Maps url", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.twoRecordOnePartner;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" />`,
        });
        expect("a.btn.btn-primary").toHaveAttribute(
            "href",
            "https://www.google.com/maps/dir/?api=1&waypoints=Chauss%C3%A9e%20de%20Louvain%2094%2C%205310%20%C3%89ghez%C3%A9e",
            { message: "The link's URL should contain the address" }
        );
        await contains(".leaflet-marker-icon").click();
        expect("div.leaflet-popup a.btn.btn-primary").toHaveAttribute(
            "href",
            "https://www.google.com/maps/dir/?api=1&destination=Chauss%C3%A9e%20de%20Louvain%2094%2C%205310%20%C3%89ghez%C3%A9e",
            { message: "The URL of the link should contain the address" }
        );
    });

    test("test the position of pin", async () => {
        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" />`,
        });

        expect(".o-map-renderer--marker").toHaveCount(1, {
            message: "Should have one marker created",
        });
        expect("div.leaflet-marker-icon .o-map-renderer--marker-badge").toHaveText("2", {
            message: "There should be a marker for two records",
        });
        const renderer = getMapRenderer(view);
        expect(renderer.markers[0].getLatLng().lat).toBe(10, {
            message: "The latitude should be the same as the record",
        });
        expect(renderer.markers[0].getLatLng().lng).toBe(10.5, {
            message: "The longitude should be the same as the record",
        });
    });

    /**
     * data: two located records
     * Create an empty map
     */
    test("Create of a empty map", async () => {
        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;

        const view = await mountView({
            type: "map",
            resModel: "res.partner",
            arch: `<map />`,
        });
        const controller = getMapController(view);
        expect(controller.model.metaData.resPartnerField).toBe(null, {
            message: "the resPartnerField should not be set",
        });

        expect(".o_map_view").toHaveClass("o_view_controller");
        expect(".leaflet-map-pane").toHaveCount(1, {
            message: "If the map exists this div should exist",
        });
        expect(".leaflet-pane .leaflet-tile-pane > *").toHaveCount(1, {
            message: "The map tiles should have been happened to the DOM",
        });
        // if element o-map-renderer--container has class leaflet-container then
        // the map is mounted
        expect(".o-map-renderer--container").toHaveClass("leaflet-container", {
            message: "the map should be in the DOM",
        });

        expect(".leaflet-overlay-pane > *").toHaveCount(0, {
            message: "Should have no showing route",
        });
    });

    /**
     * two located records
     * without routing or default_order
     * normal marker icon
     * test the click on them
     */

    test("Create view with normal marker icons", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" />`,
        });
        const controller = getMapController(view);
        expect(controller.model.metaData.numbering).toBe(false, {
            message: "the numbering option should not be enabled",
        });
        expect(controller.model.metaData.routing).toBe(false, {
            message: "The routing option should not be enabled",
        });

        expect(".leaflet-marker-icon").toHaveCount(1, { message: "There should be 1 marker" });
        expect(".leaflet-overlay-pane path").toHaveCount(0);

        await contains(".leaflet-marker-icon").click();

        expect(".leaflet-popup-pane > *").toHaveCount(1, {
            message: "Should have one showing popup",
        });

        await contains("div.leaflet-container").click();
        // wait for the popup's destruction which takes a certain time...
        for (let i = 0; i < 15; i++) {
            await animationFrame();
        }

        expect(".leaflet-popup-pane > *").toHaveCount(0, {
            message: "Should not have any showing popup",
        });
    });

    /**
     * two located records
     * with default_order
     * no numbered icon
     * test click on them
     * asserts that the rpc receive the right parameters
     */

    test("Create a view with default_order", async () => {
        expect.assertions(7);

        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;
        onRpc("project.task", "web_search_read", ({ kwargs }) => {
            expect(kwargs.order).toBe("name ASC", {
                message: "The sorting order should be on the field name in a ascendant way",
            });
        });

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" default_order="name" />`,
        });
        const controller = getMapController(view);
        expect(controller.model.metaData.numbering).toBe(false, {
            message: "the numbering option should not be enabled",
        });
        expect(controller.model.metaData.routing).toBe(false, {
            message: "The routing option should not be enabled",
        });
        expect("div.leaflet-marker-icon").toHaveCount(1, { message: "There should be 1 marker" });
        expect("div.leaflet-marker-icon .o-map-renderer--marker-badge").toHaveText("2", {
            message: "There should be a marker for two records",
        });
        expect(".leaflet-popup-pane > *").toHaveCount(0, {
            message: "Should have no showing popup",
        });
        await contains("div.leaflet-marker-icon").click();
        expect(".leaflet-popup-pane > *").toHaveCount(1, {
            message: "Should have one showing popup",
        });
    });

    /**
     * two locted records
     * with routing enabled
     * numbered icon
     * test click on route
     */

    test("Create a view with routing", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        const controller = getMapController(view);
        expect(controller.model.metaData.numbering).toBe(true, {
            message: "the numbering option should be enabled",
        });
        expect(controller.model.metaData.routing).toBe(true, {
            message: "The routing option should be enabled",
        });

        expect(controller.model.data.numberOfLocatedRecords).toBe(2, {
            message: "Should have 2 located Records",
        });
        expect(controller.model.data.routes.length).toBe(1, {
            message: "Should have 1 computed route",
        });
        expect("div.leaflet-marker-icon .o-map-renderer--marker-badge").toHaveText("2", {
            message: "There should be a marker for two records",
        });
        expect("path.leaflet-interactive").toHaveAttribute("stroke", "blue", {
            message: "The route should be blue if it has not been clicked",
        });
        expect("path.leaflet-interactive").toHaveAttribute("stroke-opacity", "0.3", {
            message: "The opacity of the polyline should be 0.3",
        });
        // the element isn't visible
        await contains("path.leaflet-interactive", { visible: false }).click();
        await animationFrame();
        expect("path.leaflet-interactive").toHaveAttribute("stroke", "darkblue", {
            message: "The route should be darkblue after being clicked",
        });
        expect("path.leaflet-interactive").toHaveAttribute("stroke-opacity", "1", {
            message: "The opacity of the polyline should be 1",
        });
    });

    test("Resequence records", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });
        const taskRecords = [
            {
                id: 1,
                name: "Project 1",
                sequence: 3,
                partner_id: 1,
            },
            {
                id: 2,
                name: "Project 2",
                sequence: 4,
                partner_id: 1,
            },
            {
                id: 3,
                name: "Project 3",
                sequence: 5,
                partner_id: 1,
            },
            {
                id: 4,
                name: "Project 4",
                sequence: 6,
                partner_id: 1,
            },
            {
                id: 5,
                name: "Project 5",
                sequence: 7,
                partner_id: 1,
            },
        ];
        Task._records = taskRecords;

        let resequenceCalled = false;

        patchWithCleanup(MapModel.prototype, {
            async _maxBoxAPI(metaData, data) {
                if (resequenceCalled) {
                    // Verify that the API is called with the records correctly ordered
                    const ids = data.records.map((record) => record.id);
                    expect.step(`API called ${ids}`);
                }
            },
        });

        onRpc("/web/dataset/resequence", async (request) => {
            const { params: args } = await request.json();
            expect.step(`resequence ${args.model} ${args.field} ${args.offset} ${args.ids}`);
            resequenceCalled = true;
        });
        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `
                <map res_partner="partner_id" routing="1" default_order="sequence" allow_resequence="true">
                    <field name="sequence"/>
                </map>
            `,
        });
        const controller = getMapController(view);
        expect(controller.model.metaData.allowResequence).toBe(true, {
            message: "The resequence option should be activated",
        });
        expect(controller.model.metaData.defaultOrder.name).toBe("sequence");

        expect(".o_row_handle").toHaveCount(5, {
            message: "Should have one row handle per record",
        });

        expect(queryAllTexts(".o-map-renderer--pin-list-details li")).toEqual([
            "1. Project 1",
            "2. Project 2",
            "3. Project 3",
            "4. Project 4",
            "5. Project 5",
        ]);

        await contains(".o-map-renderer--pin-located:nth-child(2) .o_row_handle").dragAndDrop(
            ".o-map-renderer--pin-located:nth-child(4) .o_row_handle"
        );
        await animationFrame();

        expect(queryAllTexts(".o-map-renderer--pin-list-details li")).toEqual([
            "1. Project 1",
            "2. Project 3",
            "3. Project 4",
            "4. Project 2",
            "5. Project 5",
        ]);

        expect.verifySteps(["resequence project.task sequence 4 3,4,2", "API called 1,3,4,2,5"]);
    });

    test("When resequencing, model get notified before the backend call", async () => {
        const taskRecords = [
            {
                id: 1,
                name: "Project 1",
                sequence: 3,
                partner_id: 1,
            },
            {
                id: 2,
                name: "Project 2",
                sequence: 4,
                partner_id: 1,
            },
        ];
        Task._records = taskRecords;
        const defer = new Deferred();
        onRpc("/web/dataset/resequence", async (request) => {
            const { params: args } = await request.json();
            await defer;
            expect.step(`resequence ${args.model} ${args.field} ${args.offset} ${args.ids}`);
        });
        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `
                <map res_partner="partner_id" routing="1" default_order="sequence" allow_resequence="true">
                    <field name="sequence"/>
                </map>
            `,
        });

        expect(queryAllTexts(".o-map-renderer--pin-list-details li")).toEqual([
            "1. Project 1",
            "2. Project 2",
        ]);

        await contains(".o-map-renderer--pin-located:nth-child(1) .o_row_handle").dragAndDrop(
            ".o-map-renderer--pin-located:nth-child(2) .o_row_handle"
        );
        await animationFrame();

        // Model got notified before the backend resequence call
        expect(queryAllTexts(".o-map-renderer--pin-list-details li")).toEqual([
            "1. Project 2",
            "2. Project 1",
        ]);

        defer.resolve();
        await animationFrame();
        expect.verifySteps(["resequence project.task sequence 3 2,1"]);
    });

    test("Create a view with routingError", async () => {
        expect.assertions(1);
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });
        patchWithCleanup(MapModel.prototype, {
            async _maxBoxAPI(metaData, data) {
                data.routingError = "this is test warning";
                data.routes = [];
            },
        });

        Task._records = [
            { id: 1, name: "FooProject", sequence: 1 },
            { id: 2, name: "BarProject", sequence: 2 },
        ];
        Partner._records = [];

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });

        expect(".o-map-renderer .o-map-renderer--alert").toHaveCount(1, {
            message: "should have alert",
        });
    });

    /**
     * routing with token and one located record
     * No route
     */
    test("create a view with routing and one located record", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.oneLocatedRecord;

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        const controller = getMapController(view);
        expect(controller.model.metaData.routing).toBe(true, {
            message: "The routing option should be enabled",
        });
        expect(controller.model.data.routes.length).toBe(0, {
            message: "Should have no computed route",
        });
    });

    /**
     * no mapbox token
     * assert that the view uses the right api and routes
     */
    test("CreateView with empty mapbox token setting", async () => {
        Task._records = TEST_RECORDS.task.recordWithouthPartner;
        Partner._records = [];

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" />`,
        });
        const controller = getMapController(view);
        expect(controller.model.metaData.mapBoxToken).toBe("", {
            message: "The token should be an empty string",
        });
        expect(controller.model.data.useMapBoxAPI).toBe(false, {
            message: "model should not use mapbox",
        });
    });

    /**
     * wrong mapbox token
     * assert that the view uses the openstreetmap api
     */
    test("Create a view with wrong map box setting", async () => {
        patchWithCleanup(session, { map_box_token: "vrve" });

        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        const controller = getMapController(view);
        expect(controller.model.metaData.mapBoxToken).toBe("vrve", {
            message: "The token should be kept",
        });
        expect(controller.model.data.useMapBoxAPI).toBe(false, {
            message: "model should not use mapbox",
        });
    });

    /**
     * wrong mapbox token fails at catch at route computing
     */
    test("create a view with wrong map box setting and located records", async () => {
        patchWithCleanup(session, { map_box_token: "frezfre" });

        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressCoordinates;

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        const controller = getMapController(view);
        expect(controller.model.metaData.mapBoxToken).toBe("frezfre", {
            message: "The token should be kept",
        });
        expect(controller.model.data.useMapBoxAPI).toBe(false, {
            message: "model should not use mapbox",
        });
    });

    /**
     * create view with right map box token
     * assert that the view uses the map box api
     */
    test("Create a view with the right map box token", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.recordWithouthPartner;
        Partner._records = [];

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        const controller = getMapController(view);
        expect(controller.model.metaData.mapBoxToken).toBe("token", {
            message: "The token should be the right token",
        });
        expect(controller.model.data.useMapBoxAPI).toBe(true, {
            message: "model should not use mapbox",
        });
    });

    /**
     * data: two located records
     */

    test("Click on pin shows popup, click on another shuts the first and open the other", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        expect(".leaflet-pane .leaflet-popup-pane > *").toHaveCount(0, {
            message: "The popup div should be empty",
        });

        await contains("div.leaflet-marker-icon").click();
        expect(".leaflet-popup-pane > *").toHaveCount(1, {
            message: "The popup div should contain one element",
        });

        // the element isn't visible
        await contains(".leaflet-map-pane", { visible: false }).click();
        await animationFrame();
        // wait for the popup's destruction which takes a certain time...
        for (let i = 0; i < 15; i++) {
            await animationFrame();
        }
        expect(".leaflet-pane .leaflet-popup-pane > *").toHaveCount(0, {
            message: "The popup div should be empty",
        });
    });

    /**
     * data: two located records
     * asserts that all the records are shown on the map
     */
    test("assert that all the records are shown on the map", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });
        const mapX = queryOne(".leaflet-map-pane")._leaflet_pos.x;
        const mapY = queryOne(".leaflet-map-pane")._leaflet_pos.y;
        expect(mapX - queryOne("div.leaflet-marker-icon")._leaflet_pos.x).toBeLessThan(0, {
            message:
                "If the marker is currently shown on the map, the subtraction of latitude should be under 0",
        });
        expect(mapY - queryOne("div.leaflet-marker-icon")._leaflet_pos.y).toBeLessThan(0);
        expect("div.leaflet-marker-icon .o-map-renderer--marker-badge").toHaveText("2", {
            message: "There should be a marker for two records",
        });
    });

    /**
     * data: two located records
     * asserts that the right fields are shown in the popup
     */

    test("Content of the marker popup with one field", async () => {
        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressCoordinates;

        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        const view = await mountView({
            config: { views: [[false, "form"]] },
            type: "map",
            resModel: "project.task",
            arch: `
                <map res_partner="partner_id" routing="1" hide_name="1" hide_address="1">
                    <field name="name" string="Name" />
                </map>
            `,
        });
        const controller = getMapController(view);
        expect(controller.model.metaData.fieldNamesMarkerPopup[0].fieldName).toBe("name");

        await contains("div.leaflet-marker-icon").click();

        expect(controller.model.metaData.fieldNamesMarkerPopup.length).toBe(1, {
            message: "fieldsMarkerPopup should contain one field",
        });
        expect("tbody tr").toHaveCount(1, { message: "The popup should have one field" });
        expect("tbody tr").toHaveText("Name Foo", {
            message: "Field row's text should be 'Name Foo'",
        });
        expect(".o-map-renderer--popup-buttons > *").toHaveCount(3, {
            message: "The popup should contain 2 buttons and one divider",
        });
    });

    test("Content of the marker popup with date time", async () => {
        mockTimeZone(+2); // UTC+2
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.twoRecordsFieldDateTime;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressCoordinates.map((r) => ({ ...r }));
        Partner._records[0].partner_latitude = 11.0;

        await mountView({
            config: { views: [[false, "form"]] },
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="true" hide_name="true" hide_address="true">
                    <field name="scheduled_date" string="Date"/>
                </map>`,
        });

        await contains("div.leaflet-marker-icon:first-child").click();

        expect("tbody tr .o-map-renderer--popup-table-content-value").toHaveCount(0, {
            message: "It should not contains a value node because it's not scheduled",
        });

        await contains("div.leaflet-marker-icon:last-child").click();

        expect("tbody tr .o-map-renderer--popup-table-content-value").toHaveText(
            "2022-02-07 23:09:31",
            { message: 'The time  "2022-02-07 21:09:31" should be in the local timezone' }
        );
    });

    /**
     * data: two located records
     * asserts that no field is shown in popup
     */

    test("Content of the marker with no field", async () => {
        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressNoCoordinates;
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });
        await mountView({
            config: { views: [[false, "form"]] },
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" hide_name="1" hide_address="1" />`,
        });
        await contains("div.leaflet-marker-icon").click();

        expect("tbody > *").toHaveCount(0, {
            message: "The popup should have only the button",
        });
        expect(".o-map-renderer--popup-buttons > *").toHaveCount(3, {
            message: "The popup should contain 2 buttons and one divider",
        });
    });

    test("Attribute: hide_name", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressCoordinates;
        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" hide_name="1" />`,
        });

        await contains("div.leaflet-marker-icon").click();

        expect("tbody > tr").toHaveCount(1, { message: "The popup should have one field" });
        expect("tbody tr .o-map-renderer--popup-table-content-name").toHaveText("Address", {
            message: "The popup should have address field",
        });
    });

    test("Render partner address field in popup", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.oneLocatedRecord;
        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" hide_name="1" />`,
        });

        await contains("div.leaflet-marker-icon").click();

        expect("tbody tr").toHaveCount(1, { message: "The popup should have one field" });
        expect("tbody tr .o-map-renderer--popup-table-content-name").toHaveText("Address", {
            message: "The popup should have address field",
        });
        expect("tbody tr .o-map-renderer--popup-table-content-value").toHaveText(
            "Chaussée de Namur 40, 1367, Ramillies",
            { message: "The popup should have correct address" }
        );
    });

    test("Hide partner address field in popup", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.oneLocatedRecord;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" hide_address="1" />`,
        });

        await contains("div.leaflet-marker-icon").click();

        expect("tbody tr").toHaveCount(1, { message: "The popup should have one field" });
        expect("tbody tr .o-map-renderer--popup-table-content-name").toHaveText("Name", {
            message: "The popup should have name field",
        });
        expect("tbody tr .o-map-renderer--popup-table-content-value").toHaveText("Foo", {
            message: "The popup should have correct address",
        });
    });

    test("Handle records of same co-ordinates in marker", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.twoRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressCoordinates;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" />`,
        });

        expect("div.leaflet-marker-icon").toHaveCount(1, {
            message: "There should be a one marker",
        });
        expect("div.leaflet-marker-icon .o-map-renderer--marker-badge").toHaveText("2", {
            message: "There should be a marker for two records",
        });

        await contains("div.leaflet-marker-icon").click();

        expect("tbody tr").toHaveCount(1, { message: "The popup should have one field" });
        expect("tbody tr .o-map-renderer--popup-table-content-name").toHaveText("Address", {
            message: "The popup should have address field",
        });
    });

    test("Pager", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = Array.from({ length: 101 }, (_, index) => ({
            id: index + 1,
            name: "project",
            partner_id: index + 1,
        }));
        Partner._records = Array.from({ length: 101 }, (_, index) => ({
            id: index + 1,
            name: "Foo",
            partner_latitude: 10.0,
            partner_longitude: 10.5,
        }));

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" />`,
        });
        expect(".o_pager").toHaveCount(1);
        expect(`.o_pager_counter .o_pager_value`).toHaveText("1-80", {
            message: "current pager value should be 1-20",
        });
        expect(`.o_pager_counter span.o_pager_limit`).toHaveText("101", {
            message: "current pager limit should be 21",
        });

        await contains(`.o_pager button.o_pager_next`).click();

        expect(`.o_pager_counter .o_pager_value`).toHaveText("81-101", {
            message: "pager value should be 21-40",
        });
    });

    test("New domain", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = [
            { id: 1, name: "FooProject", sequence: 1, partner_id: 1 },
            { id: 2, name: "BarProject", sequence: 2, partner_id: 2 },
        ];
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressCoordinates;

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
            searchViewArch: `
                <search>
                    <filter name="f_1" string="Filter 1" domain="[('name', '=', 'FooProject')]"/>
                    <filter name="f_2" string="Filter 2" domain="[('name', '=', 'Foofezfezf')]"/>
                    <filter name="f_3" string="Filter 3" domain="[('name', 'like', 'Project')]"/>
                </search>
            `,
        });
        const controller = getMapController(view);
        expect(controller.model.data.records).toHaveLength(2, {
            message: "There should be 2 records",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(1);
        expect("div.leaflet-marker-icon .o-map-renderer--marker-badge").toHaveText("2", {
            message: "There should be a marker for two records",
        });

        await toggleSearchBarMenu();
        await toggleMenuItem("Filter 1");

        expect(controller.model.data.records).toHaveLength(1, {
            message: "There should be 1 record",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
        expect("div.leaflet-marker-icon").toHaveCount(1, {
            message: "There should be 1 marker on the map",
        });

        await toggleMenuItem("Filter 1");
        await toggleMenuItem("Filter 2");

        expect(controller.model.data.records).toHaveLength(0, {
            message: "There should be no record",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(0);
        expect("div.leaflet-marker-icon").toHaveCount(0, {
            message: "There should be 0 marker on the map",
        });

        await toggleMenuItem("Filter 2");
        await toggleMenuItem("Filter 3");

        expect(controller.model.data.records).toHaveLength(2, {
            message: "There should be 2 record",
        });
        expect(".leaflet-overlay-pane path").toHaveCount(1);
        expect("div.leaflet-marker-icon").toHaveCount(1, {
            message: "There should be 1 marker on the map",
        });
        expect("div.leaflet-marker-icon .o-map-renderer--marker-badge").toHaveText("2", {
            message: "There should be a marker for two records",
        });
    });

    test("Toggle grouped pin lists", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.threeRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressCoordinates;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" />`,
            groupBy: ["partner_id"],
        });

        expect(".o-map-renderer--pin-list-group-header").toHaveCount(2, {
            message: "Should have 2 groups",
        });
        expect(queryAllTexts(".o-map-renderer--pin-list-group-header")).toEqual(["Bar", "Foo"]);
        expect(".o-map-renderer--pin-list-details").toHaveCount(2);
        expect(".o-map-renderer--pin-list-details li").toHaveCount(3);
        expect(queryAllTexts(".o-map-renderer--pin-list-details")).toEqual([
            "FooProject\nFooBarProject",
            "BarProject",
        ]);

        await contains(".o-map-renderer--pin-list-group-header:eq(1)").click();

        expect(".o-map-renderer--pin-list-group-header").toHaveCount(2, {
            message: "Should still have 2 groups",
        });
        expect(".o-map-renderer--pin-list-details").toHaveCount(1);
        expect(".o-map-renderer--pin-list-details li").toHaveCount(2);
        expect(queryAllTexts(".o-map-renderer--pin-list-details")).toEqual([
            "FooProject\nFooBarProject",
        ]);

        await contains(".o-map-renderer--pin-list-group-header:eq(0)").click();

        expect(".o-map-renderer--pin-list-details").toHaveCount(0);

        await contains(".o-map-renderer--pin-list-group-header:eq(1)").click();

        expect(".o-map-renderer--pin-list-details").toHaveCount(1);
        expect(".o-map-renderer--pin-list-details li").toHaveCount(1);
        expect(queryAllTexts(".o-map-renderer--pin-list-details")).toEqual(["BarProject"]);
    });

    test("Toggle grouped one2many pin lists", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.threeRecords.map((r) => ({ ...r }));
        Task._records[1].partner_ids = [1, 3];

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id"/>`,
            groupBy: ["partner_ids"],
        });

        expect(".o-map-renderer--pin-list-group-header").toHaveCount(3, {
            message: "Should have 3 groups",
        });

        expect(queryAllTexts(".o-map-renderer--pin-list-group-header")).toEqual([
            "Foo",
            "Foo",
            "Bar",
        ]);

        expect(".o-map-renderer--pin-list-details").toHaveCount(3);
        expect(".o-map-renderer--pin-list-details li").toHaveCount(5);
        expect(queryAllTexts(".o-map-renderer--pin-list-details")).toEqual([
            "FooProject\nBarProject\nFooBarProject",
            "FooProject",
            "BarProject",
        ]);
        expect(".leaflet-marker-icon").toHaveCount(3);
    });

    test("Check groupBy on datetime field", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._fields["scheduled_date"] = fields.Datetime({
            string: "Schedule date",
        });
        Task._records = [
            { id: 1, name: "FooProject", sequence: 1, partner_id: 1, scheduled_date: false },
        ];
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressCoordinates;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" />`,
            searchViewId: false,
            searchViewArch: `
                <search>
                    <group expand='0' string='Group By'>
                        <filter string="scheduled_date" name="scheduled_date" context="{'group_by': 'scheduled_date'}"/>
                    </group>
                </search>
            `,
        });

        expect(".o-map-renderer--pin-list-group-header").toHaveCount(0, {
            message: "Should not have any groups",
        });

        await toggleSearchBarMenu();

        // don't throw an error when grouping a field with a false value
        await toggleMenuItem("scheduled_date");
        await toggleMenuItemOption("scheduled_date", "year");
    });

    test("Check groupBy on properties field", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Partner._fields["properties_definition"] = fields.PropertiesDefinition({
            string: "Properties Definition",
        });
        Task._fields["task_properties"] = fields.Properties({
            string: "Properties",
            definition_record: "partner_id",
            definition_record_field: "properties_definition",
        });
        Partner._records = [
            {
                id: 1,
                name: "Bar",
            },
            {
                id: 2,
                name: "Foo",
                partner_latitude: 10.0,
                partner_longitude: 10.5,
                sequence: 3,
                properties_definition: [
                    {
                        name: "bd6404492c244cff",
                        type: "char",
                        string: "Reference Number",
                    },
                ],
            },
        ];
        Task._records = [
            {
                id: 1,
                name: "FooProject",
                sequence: 1,
                partner_id: 1,
                task_properties: {
                    bd6404492c244cff: "1234",
                },
            },
        ];

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" />`,
            searchViewId: false,
            searchViewArch: `
                <search>
                    <group expand='0' string='Group By'>
                        <filter string="task_properties" name="task_properties"
                            context="{'group_by': 'task_properties'}"/>
                    </group>
                </search>
            `,
        });

        expect(".o-map-renderer--pin-list-group-header").toHaveCount(0, {
            message: "Should not have any groups",
        });

        await toggleSearchBarMenu();

        // don't throw an error when grouping on a property
        await toggleMenuItem("task_properties");
        await animationFrame();
        await contains(".o_accordion_values .o_menu_item").click();

        // check that the property has been added in the facet without crashing
        expect(`.o_facet_value:contains("Reference Number")`).toHaveCount(1);
        expect(".o-map-renderer--pin-list-group-header").toHaveCount(0);
    });

    test("Change groupBy", async () => {
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });

        Task._records = TEST_RECORDS.task.threeRecords;
        Partner._records = TEST_RECORDS.partner.twoRecordsAddressCoordinates;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" />`,
            searchViewId: false,
            searchViewArch: `
                <search>
                    <filter string="Partner" name="partner_id" context="{'group_by': 'partner_id'}"/>
                    <filter string="Name" name="name" context="{'group_by': 'name'}"/>
                </search>
            `,
        });

        expect(".o-map-renderer--pin-list-group-header").toHaveCount(0, {
            message: "Should not have any groups",
        });

        await toggleSearchBarMenu();
        await toggleMenuItem("Partner");

        expect(".o-map-renderer--pin-list-group-header").toHaveCount(2, {
            message: "Should have 2 groups",
        });
        expect(queryAllTexts(".o-map-renderer--pin-list-group-header")).toEqual(["Bar", "Foo"]);
        // Groups should be loaded too
        expect(".o-map-renderer--pin-list-details li").toHaveCount(3);
        expect(queryAllTexts(".o-map-renderer--pin-list-details")).toEqual([
            "FooProject\nFooBarProject",
            "BarProject",
        ]);

        await toggleMenuItem("Name");

        expect(queryAllTexts(".o-map-renderer--pin-list-group-header")).toEqual(["Bar", "Foo"], {
            message: "Should not have changed",
        });
        expect(queryAllTexts(".o-map-renderer--pin-list-details")).toEqual([
            "FooProject\nFooBarProject",
            "BarProject",
        ]);

        await toggleMenuItem("Partner");

        expect(".o-map-renderer--pin-list-group-header").toHaveCount(3, {
            message: "Should have 3 groups",
        });
        expect(queryAllTexts(".o-map-renderer--pin-list-group-header")).toEqual([
            "FooProject",
            "BarProject",
            "FooBarProject",
        ]);
        expect(queryAllTexts(".o-map-renderer--pin-list-details")).toEqual([
            "FooProject",
            "BarProject",
            "FooBarProject",
        ]);
        expect(".o-map-renderer--pin-list-details:eq(0) li").toHaveCount(1);
        expect(".o-map-renderer--pin-list-details:eq(1) li").toHaveCount(1);
        expect(".o-map-renderer--pin-list-details:eq(2) li").toHaveCount(1);
    });

    //--------------------------------------------------------------------------
    // Controller testing
    //--------------------------------------------------------------------------

    test("Click on open button switches to form view", async () => {
        mockService("action", {
            switchView(name, props) {
                expect.step("switchView");
                expect(name).toBe("form", { message: "The view switched to should be form" });
                expect(props).toEqual({ resId: 1 }, { message: "Props should be correct" });
            },
        });

        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.oneLocatedRecord;

        await mountView({
            config: { views: [[false, "form"]] },
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1" />`,
        });

        await contains("div.leaflet-marker-icon").click();
        expect(
            "div.leaflet-popup-pane button.btn.btn-primary.o-map-renderer--popup-buttons-open"
        ).toHaveCount(1, { message: "The button should be present in the dom" });
        await contains(
            "div.leaflet-popup-pane button.btn.btn-primary.o-map-renderer--popup-buttons-open"
        ).click();
        expect.verifySteps(["switchView"]);
    });

    test("Test the lack of open button", async () => {
        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.oneLocatedRecord;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id"></map>`,
        });

        await contains("div.leaflet-marker-icon").click();

        expect(
            "div.leaflet-popup-pane button.btn.btn-primary.o-map-renderer--popup-buttons-open"
        ).toHaveCount(0, { message: "The button should not be present in the dom" });
    });

    test("attribute panel_title on the arch should display in the pin list", async () => {
        Task._records = TEST_RECORDS.task.oneRecord;
        Partner._records = TEST_RECORDS.partner.oneLocatedRecord;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" panel_title="AAAAAAAAAAAAAAAAA"></map>`,
        });

        expect(".o-map-renderer--pin-list-container .o_pin_list_header span").toHaveText(
            "AAAAAAAAAAAAAAAAA"
        );
    });

    test("Test using a field other than partner_id for the map view", async () => {
        Task._records = TEST_RECORDS.task.anotherPartnerId;
        Partner._records = TEST_RECORDS.partner.oneLocatedRecord;

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="another_partner_id"></map>`,
        });

        await contains("div.leaflet-marker-icon").click();

        expect(
            "div.leaflet-popup-pane button.btn.btn-primary.o-map-renderer--popup-buttons-open"
        ).toHaveCount(0, { message: "The button should not be present in the dom" });
    });

    test("Check Google Maps URL is updating on domain change", async () => {
        Task._records = [
            { id: 1, name: "FooProject", sequence: 1, partner_id: 2 },
            { id: 2, name: "BarProject", sequence: 2, partner_id: 3 },
        ];

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id"/>`,
            searchViewArch: `
                        <search>
                            <filter name="some_filter" string="FooProject only" domain="[['name', '=', 'FooProject']]"/>
                        </search>`,
        });

        expect("a.btn.btn-primary").toHaveAttribute(
            "href",
            "https://www.google.com/maps/dir/?api=1&waypoints=Chauss%C3%A9e%20de%20Namur%2040%2C%201367%2C%20Ramillies|Chauss%C3%A9e%20de%20Wavre%2050%2C%201367%2C%20Ramillies",
            { message: "The link's URL initially should contain the addresses for all records" }
        );

        //apply domain and check that the Google Maps URL on the button reflects the changes
        await toggleSearchBarMenu();
        await toggleMenuItem("FooProject only");
        expect("a.btn.btn-primary").toHaveAttribute(
            "href",
            "https://www.google.com/maps/dir/?api=1&waypoints=Chauss%C3%A9e%20de%20Namur%2040%2C%201367%2C%20Ramillies",
            {
                message:
                    "The link's URL after domain is applied should only contain addresses for filtered records",
            }
        );
    });

    test("Check Google Maps URL (routing and multiple records)", async () => {
        Task._records = [
            { id: 1, name: "FooProject", sequence: 1, partner_id: 2 },
            { id: 2, name: "BarProject", sequence: 2, partner_id: 3 },
        ];

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1"/>`,
        });

        expect("a.btn.btn-primary").toHaveAttribute(
            "href",
            "https://www.google.com/maps/dir/?api=1&destination=Chauss%C3%A9e%20de%20Wavre%2050%2C%201367%2C%20Ramillies&waypoints=Chauss%C3%A9e%20de%20Namur%2040%2C%201367%2C%20Ramillies",
            { message: "The link's URL initially should contain the addresses for all records" }
        );
    });

    test("Do not notify if unmounted after fetching coordinate", async () => {
        const def = new Deferred();

        patchWithCleanup(MapModel.prototype, {
            _fetchCoordinatesFromAddressOSM() {
                return def;
            },
            _notifyFetchedCoordinate() {
                expect.step("notify");
            },
        });

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1"/>`,
        });
        const controller = getMapController(view);

        destroy(controller);

        def.resolve();
        await animationFrame();

        expect.verifySteps([]);
    });

    test("Do not fetch if unmounted after waiting interval", async () => {
        patchWithCleanup(MapModel.prototype, {
            async _fetchCoordinatesFromAddressOSM() {
                expect.step("_fetchCoordinatesFromAddressOSM");
            },
            _notifyFetchedCoordinate() {
                expect.step("_notifyFetchedCoordinate");
            },
            _openStreetMapAPIAsync() {
                expect.step("_openStreetMapAPIAsync");
                return super._openStreetMapAPIAsync(...arguments);
            },
        });

        const view = await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" routing="1"/>`,
        });
        const controller = getMapController(view);

        destroy(controller);
        await animationFrame();

        expect.verifySteps(["_openStreetMapAPIAsync"]);
    });

    test("Check groupBy on selection field", async () => {
        expect.assertions(1);
        patchWithCleanup(session, { map_box_token: MAP_BOX_TOKEN });
        Task._records = [
            { id: 1, name: "Project", sequence: 1, partner_id: 1, task_status: "abc" },
        ];
        onRpc(
            "res.partner",
            "search_read",
            () => TEST_RECORDS.partner.twoRecordsAddressCoordinates
        );

        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id" />`,
            groupBy: ["task_status"],
        });
        expect(".o-map-renderer--pin-list-group-header").toHaveCount(1, { message: "ABC" });
    });
});

describe.tags("mobile");
describe("map_view_mobile", () => {
    test("use pin list container on mobile", async () => {
        await mountView({
            type: "map",
            resModel: "project.task",
            arch: `<map res_partner="partner_id">
                    <field name="name" string="Project"/>
                </map>`,
        });

        expect(".o_pin_list_header .fa.fa-caret-left").toHaveCount(1);
        expect(".o_pin_list_header .fa.fa-caret-down").toHaveCount(0);

        await contains(".o_pin_list_header").click();
        expect(".o-sm-pin-list-container.h-100").toHaveCount(1, {
            message: "There should extend the pin list container",
        });
        expect(".o_pin_list_header .fa.fa-caret-down").toHaveCount(1);
        expect(".o_pin_list_header .fa.fa-caret-left").toHaveCount(0);

        await contains(".o_pin_list_header").click();
        expect(".o_pin_list_header .fa.fa-caret-left").toHaveCount(1);
        expect(".o_pin_list_header .fa.fa-caret-down").toHaveCount(0);
        expect(".o-sm-pin-list-container.h-100").toHaveCount(0, {
            message: "There should collapse the pin list container",
        });
    });
});
