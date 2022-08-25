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
                        priority: { string: "Priority", type: "selection", selection: [['0', 'normal'],['1', 'important']]},
                        slowField: { string: "Hard to Compute", type: "char" },
                    },
                    records: [
                        { id: 1, priority: '0', name: "Daniel Fortesque" },
                        { id: 2, priority: '0', name: "Samuel Oak" },
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
                    if (route === "/web/dataset/call_kw/person/search_read") {
                        const fields = args.args[1];
                        const recs = [];
                        for (const d of this.data.person.records) {
                            d["slowField"] = `${d.name} ${d.id}`;
                            recs.push(d);
                        }
                        // Don't wait if it read only one record
                        if (fields.includes("slowField")) {
                            await promiseRead;
                        }
                        return Promise.resolve(recs);
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

        QUnit.test("With the priority widget", async function (assert) {
            assert.expect(19);
            const promiseRead = makeDeferred();
            const list = await createView({
                View: LazyColumnList,
                model: "person",
                data: this.data,
                arch:
                    '<tree editable="top" js_class="lazy_column_list">' +
                    '<field name="name"/>' +
                    '<field name="priority" widget="priority"/>' +
                    '<field name="slowField" options=\'{"lazy": true}\'/>' +
                    "</tree>",
                mockRPC: async function (route, args) {
                    if (route === "/web/dataset/call_kw/person/search_read" ||
                        route === "/web/dataset/call_kw/person/read") {
                        var record_ids = args.args[0];
                        if (route === "/web/dataset/call_kw/person/search_read"){
                            record_ids = [1, 2]
                        } 
                        const fields = args.args[1];
                        const recs = [];
                        for (const d of this.data.person.records) {
                            if (record_ids.includes(d.id)) {
                                d["slowField"] = `${d.name} ${d.id} ${d.priority}`;
                                recs.push(d);
                            }
                        }
                        // Don't wait if it read only one record
                        if (fields.includes("slowField") && record_ids.length > 1) {
                            await promiseRead;
                        }
                        return Promise.resolve(recs);
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

            assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.fa-star').length, 0,
                "widget shouldn't be considered set");
            await testUtils.dom.click(list.$('.o_data_row').first().find('.o_priority a.fa-star-o').first());
            
            assert.strictEqual(list.$('.o_data_row').first().find('.o_priority a.fa-star').length, 1,
                "widget should be considered set");
            $spin = list.$el.find("th[data-name='slowField'] .fa.fa-spin");
            $results = list.$el.find("td[name='slowField']");
            assert.equal($spin.length, 1);
            assert.equal($spin.hasClass("invisible"), false);
            assert.equal($results.length, 2);
            assert.equal($results.first().text(), "Daniel Fortesque 1 1", 
                "It should be read by the click on priority");
            assert.equal($results.last().text(), "");

            promiseRead.resolve();
            await nextTick();

            $spin = list.$el.find("th[data-name='slowField'] .fa.fa-spin");
            $results = list.$el.find("td[name='slowField']");
            assert.equal($spin.length, 1);
            assert.equal($spin.hasClass("invisible"), true);
            assert.equal($results.length, 2);
            assert.equal($results.first().text(), "Daniel Fortesque 1 1", 
                "It shouldn't be erase the data from priority click because this data is newer");
            assert.equal($results.last().text(), "Samuel Oak 2 0");

            assert.containsN(list, ".o_data_row", 2, "should have 2 records");

            list.destroy();
        });
    }
);
