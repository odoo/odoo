$(document).ready(function () {
    var $fix = $('#qunit-fixture');
    var xhr = QWeb2.Engine.prototype.get_xhr();
    xhr.open('GET', '/web/static/src/xml/base.xml', false);
    xhr.send(null);
    var doc = xhr.responseXML;

    var noop = function () {};
    /**
     * Make connection RPC responses mockable by setting keys on the
     * Connection#responses object (key is the URL, value is the function to
     * call with the RPC request payload)
     *
     * @param {openerp.web.Connection} connection connection instance to mockify
     * @param {Object} [responses] url:function mapping to seed the mock connection
     */
    var mockifyRPC = function (connection, responses) {
        connection.responses = responses || {};
        connection.rpc_function = function (url, payload) {
            if (!(url.url in this.responses)) {
                return $.Deferred().reject({}, 'failed', _.str.sprintf("Url %s not found in mock responses", url.url)).promise();
            }
            return $.when(this.responses[url.url](payload));
        };
    };

    var instance;
    var baseSetup = function () {
        instance = window.openerp.init([]);
        window.openerp.web.corelib(instance);
        window.openerp.web.coresetup(instance);
        window.openerp.web.chrome(instance);
        window.openerp.web.data(instance);
        window.openerp.web.views(instance);
        window.openerp.web.list(instance);
        window.openerp.web.form(instance);
        window.openerp.web.list_editable(instance);

        instance.web.qweb.add_template(doc);

        mockifyRPC(instance.connection);
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
