odoo.define("base.abstract_controller_tests", function(require) {
    "use strict";

    var testUtils = require("web.test_utils");
    var createView = testUtils.createView;
    var BasicView = require("web.BasicView");
    var BasicRenderer = require("web.BasicRenderer");

    function getHtmlRenderer(html) {
        return BasicRenderer.extend({
            start: function() {
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

    QUnit.module(
        "Views",
        {
            beforeEach: function() {
                this.data = {
                    test_model: {
                        fields: {},
                        records: []
                    }
                };
            }
        },
        function() {

            QUnit.module('AbstractController');

            QUnit.test(
                'click on a a[type="action"] child triggers the correct action',
                function(assert) {
                    assert.expect(3);

                    var html =
                        "<div>" +
                            '<a name="a1" type="action" class="simple">simple</a>' +
                            '<a name="a2" type="action" class="with-child">' +
                                "<span>child</input>" +
                            "</a>" +
                        "</div>";

                    var view = createView({
                        View: getHtmlView(html, "test"),
                        data: this.data,
                        model: "test_model",
                        arch: "<test/>",
                        intercepts: {
                            do_action: function(event) {
                                assert.step(event.data.action);
                            }
                        }
                    });
                    view.$(".simple").click();
                    view.$(".with-child span").click();
                    assert.verifySteps(["a1", "a2"]);

                    view.destroy();
                }
            );
        }
    );
});
