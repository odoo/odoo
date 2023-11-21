odoo.define("board.dashboard_tests", function (require) {
    "use strict";

    var BoardView = require("board.BoardView");
    var testUtils = require("web.test_utils");
    var createView = testUtils.createView;

    QUnit.module("Board view", {
        beforeEach: function () {
            this.data = {
                board: {
                    fields: {},
                    records: [],
                },
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            foo: "yop",
                        },
                    ],
                },
            };
        },
    });

    QUnit.test("can't switch views in the dashboard", async function (assert) {
        assert.expect(3);

        var target = await createView({
            View: BoardView,
            model: "board",
            data: this.data,
            arch: `<form string="My Dashboard">
                <board style="2-1">
                    <column>
                        <action context="{}" domain="[]" view_mode="list" string="ABC" name="51"/>
                    </column>
                </board>
            </form>`,
            mockRPC: function (route) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [
                            [4, "list"],
                            [5, "form"],
                        ],
                    });
                }
                return this._super.apply(this, arguments);
            },
            archs: {
                "partner,4,list": `<tree string="Partner"><field name="foo"/></tree>`,
            },
        });

        assert.containsNone(target, ".oe_dashboard_links", "Couldn't allow user to Change layout");
        assert.containsOnce(target, ".oe_dashboard_layout_1", "The display layout is force to 1");
        assert.containsNone(
            target,
            ".o_action .o_control_panel",
            "views in the dashboard do not have a control panel"
        );

        target.destroy();
    });

    QUnit.test("Correctly soft switch to '1' layout on small screen", async function (assert) {
        assert.expect(2);

        var target = await createView({
            View: BoardView,
            model: "board",
            data: this.data,
            arch: `<form>
                <board style="2-1">
                        <column>
                            <action context="{}" domain="[]" view_mode="list" string="ABC" name="51"/>
                        </column>
                        <column>
                            <action context="{}" domain="[]" view_mode="list" string="ABC" name="51"/>
                        </column>
                    </board>
            </form>`,
            mockRPC: function (route) {
                if (route === "/web/action/load") {
                    return Promise.resolve({
                        res_model: "partner",
                        views: [
                            [4, "list"],
                            [5, "form"],
                        ],
                    });
                }
                return this._super.apply(this, arguments);
            },
            archs: {
                "partner,4,list": '<tree string="Partner"><field name="foo"/></tree>',
            },
        });

        assert.containsOnce(target, ".oe_dashboard_layout_1", "The display layout is force to 1");
        assert.containsN(target, ".oe_action", 2, "The display should contains the 2 actions");

        target.destroy();
    });

    QUnit.test("empty board view", async function (assert) {
        assert.expect(2);
        const target = await createView({
            View: BoardView,
            debug: 1,
            model: "board",
            data: this.data,
            arch: `<form string="My Dashboard">
                <board style="2-1">
                    <column/>
                </board>
            </form>`,
            archs: {
                "partner,4,list": '<tree string="Partner"><field name="foo"/></tree>',
            },
        });

        assert.hasClass(
            target.renderer.$el,
            "o_dashboard",
            "with a dashboard, the renderer should have the proper css class"
        );
        assert.containsOnce(
            target,
            ".o_dashboard .o_view_nocontent",
            "should have a no content helper"
        );

        target.destroy();
    });
});
