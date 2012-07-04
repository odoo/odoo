$(document).ready(function () {
    var $fix = $('#qunit-fixture');

    var instance;
    var baseSetup = function () {
        instance = openerp.testing.instanceFor('list_editable');

        openerp.testing.loadTemplate(instance);

        openerp.testing.mockifyRPC(instance);
    };
    module('editor', {
        setup: baseSetup
    });
    asyncTest('base-state', 2, function () {
        var e = new instance.web.list.Editor({
            dataset: {},
            editionView: function () {
                return {
                    arch: {
                        tag: 'form',
                        attrs: {
                            version: '7.0',
                            'class': 'oe_form_container'
                        },
                        children: []
                    }
                };
            }
        });
        e.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function () {
                ok(!e.isEditing(), "should not be editing");
                ok(e.form instanceof instance.web.FormView,
                   "should use default form type");
            });
    });
});
