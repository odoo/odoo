/** @odoo-module */

import ListView from "web.ListView";
import testUtils from "web.test_utils";
import { AddToGoogleSpreadsheet } from "../src/add_to_google_spreadsheet/add_to_google_spreadsheet";

AddToGoogleSpreadsheet.shouldBeDisplayed = (env) => true;
import { ormService } from "@web/core/orm_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import * as LegacyFavoriteMenu from "web.FavoriteMenu"
import { makeTestEnv } from "../../../web/static/tests/helpers/mock_env";
import { makeMockServer } from "../../../web/static/tests/helpers/mock_server";

const createView = testUtils.createView;

import { registry } from "@web/core/registry";
const serviceRegistry = registry.category("services");
const legacyFavoriteMenuRegistry = LegacyFavoriteMenu.registry;


QUnit.module(
    "google_spreadsheet > insert_in_google_spreadsheet_from_favorite_menu",
    {
        beforeEach: function () {
            legacyFavoriteMenuRegistry.add(
                "add-to-google-spreadsheet",
                AddToGoogleSpreadsheet,
                1
            );
            this.data = {
                foo: {
                    fields: {
                        foo: {string: "Foo", type: "char"},
                    },
                    records: [{id: 1, foo: "yop"}],
                },
            };
        },
    },
    function () {
        QUnit.test("Menu item is present in list view", async function (assert) {
            assert.expect(1);
            const list = await createView({
                View: ListView,
                model: "foo",
                data: this.data,
                services: { dialog: dialogService },
                arch: '<tree><field name="foo"/></tree>',
            });
            await testUtils.dom.click(list.$(".o_favorite_menu button"));
            assert.containsOnce(list, ".o_add_to_spreadsheet");

            list.destroy();
        });

        QUnit.test("Parameters are correct", async function (assert) {
            assert.expect(3);

            serviceRegistry.add("orm", ormService);
            const mockRPC = (route, args) => {
                if(route.includes("set_spreadsheet")){
                    assert.strictEqual(args.args.length, 4);
                    assert.strictEqual(typeof args.args[1], 'string');
                    assert.notEqual(typeof args.args[3], 'undefined');
                    return Promise.reject("erreur");
                }
            };
            makeMockServer(this.data, mockRPC);
            const env = await makeTestEnv();

            const list = await createView({
                View: ListView,
                model: "foo",
                data: this.data,
                services: {orm: env.services.orm, dialog: dialogService },
                arch: '<tree><field name="foo"/></tree>',
            });
            await testUtils.dom.click(list.$(".o_favorite_menu button"))
            await testUtils.dom.click(list.$(".o_add_to_spreadsheet"))

            list.destroy();
        });
    }
);
