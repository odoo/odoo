/** @odoo-module **/

import testUtils from "web.test_utils";
import LazyColumnList from "../src/js/lazy_column_list";
import { makeDeferred, nextTick } from "../../../web/static/tests/helpers/utils";

const createView = testUtils.createView;

QUnit.module(
    "Views",
    {
        beforeEach: function () {
            this.data = {
                person: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        slowField: { string: "Hard to Compute", type: "char" },
                    },
                    records: [
                        { id: 1, name: "Daniel Fortesque" },
                        { id: 2, name: "Samuel Oak" },
                    ],
                },
            };
        },
    },
    function () {
        QUnit.module("LazyColumnList");

        QUnit.test("Loading correctly", async function (assert) {
            assert.expect(12);
            const promiseRead = makeDeferred();
            const list = await createView({
                View: LazyColumnList,
                model: "person",
                data: this.data,
                arch:
                    '<tree editable="top" js_class="lazy_column_list">' +
                    '<field name="name"/>' +
                    '<field name="slowField" options=\'{"lazy": true}\'/>' +
                    "</tree>",
                mockRPC: async function (route, args) {
                    console.log(route);
                    if (route === "/web/dataset/call_kw/person/read") {
                        const fields = args.args[1];
                        const records = [];
                        for (const d of this.data.person.records) {
                            let reco = { id: d.id };
                            for (const f of fields) {
                                if (f === "slowField") {
                                    reco[f] = `${d.name} ${d.id}`;
                                } else {
                                    reco[f] = d[f];
                                }
                            }
                            records.push(reco);
                        }
                        await promiseRead;
                        return Promise.resolve(records);
                    }
                    return this._super.apply(this, arguments);
                },
            });
            // Checks we have initially 2 records
            assert.containsN(list, ".o_data_row", 2, "should have 2 records");

            let $spin = list.$el.find("th[data-name='slowField'] .fa.fa-spin");
            let $results = list.$el.find("td[name='slowField']");
            assert.equal($spin.length, 1);
            assert.equal($spin.hasClass("invisible"), false);
            assert.equal($results.length, 2);
            assert.equal($results.first().text(), "");
            assert.equal($results.last().text(), "");

            promiseRead.resolve();
            await nextTick();

            $spin = list.$el.find("th[data-name='slowField'] .fa.fa-spin");
            $results = list.$el.find("td[name='slowField']");
            assert.equal($spin.length, 1);
            assert.equal($spin.hasClass("invisible"), true);
            assert.equal($results.length, 2);
            assert.equal($results.first().text(), "Daniel Fortesque 1");
            assert.equal($results.last().text(), "Samuel Oak 2");

            assert.containsN(list, ".o_data_row", 2, "should have 2 records");

            list.destroy();
        });
    }
);
