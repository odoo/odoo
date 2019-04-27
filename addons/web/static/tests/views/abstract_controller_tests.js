odoo.define("base.abstract_controller_tests", function (require) {
"use strict";

var testUtils = require("web.test_utils");
var createView = testUtils.createView;
var BasicView = require("web.BasicView");
var BasicRenderer = require("web.BasicRenderer");

function getHtmlRenderer(html) {
    return BasicRenderer.extend({
        start: function () {
            this.$el.html(html);
            return this._super.apply(this, arguments);
        }
    });
}
function getHtmlView(html, viewType) {
    viewType = viewType || "test";
    return BasicView.extend({
        viewType: viewType,
        config: _.extend({}, BasicView.prototype.config, {
            Renderer: getHtmlRenderer(html)
        })
    });
}

QUnit.module("Views", {
    beforeEach: function () {
        this.data = {
            test_model: {
                fields: {},
                records: []
            }
        };
    }
}, function () {
    QUnit.module('AbstractController');

    QUnit.test('click on a a[type="action"] child triggers the correct action', async function (assert) {
        assert.expect(7);

        var html =
            "<div>" +
            '<a name="a1" type="action" class="simple">simple</a>' +
            '<a name="a2" type="action" class="with-child">' +
            "<span>child</input>" +
            "</a>" +
            '<a type="action" data-model="foo" data-method="bar" class="method">method</a>' +
            '<a type="action" data-model="foo" data-res-id="42" class="descr">descr</a>' +
            '<a type="action" data-model="foo" class="descr2">descr2</a>' +
            "</div>";

        var view = await createView({
            View: getHtmlView(html, "test"),
            data: this.data,
            model: "test_model",
            arch: "<test/>",
            intercepts: {
                do_action: function (event) {
                    assert.step(event.data.action.name || event.data.action);
                }
            },
            mockRPC: function (route, args) {
                if (args.model === 'foo' && args.method === 'bar') {
                    assert.step("method");
                    return Promise.resolve({name: 'method'});
                }
                return this._super.apply(this, arguments);
            }
        });
        await testUtils.dom.click(view.$(".simple"));
        await testUtils.dom.click(view.$(".with-child span"));
        await testUtils.dom.click(view.$(".method"));
        await testUtils.dom.click(view.$(".descr"));
        await testUtils.dom.click(view.$(".descr2"));
        assert.verifySteps(["a1", "a2", "method", "method", "descr", "descr2"]);

        view.destroy();
    }
    );
});
});
