odoo.define('web.Model', function (require) {
"use strict";

var Class = require('web.Class');
var session = require('web.session');
var utils = require('web.utils');

var Model = Class.extend({
    /**
    new openerp.web.Model([session,] model_name[, context[, domain]])

    @constructs instance.web.Model
    @extends instance.web.Class

    @param {openerp.web.Session} [session] The session object used to communicate with
    the server.
    @param {String} model_name name of the OpenERP model this object is bound to
    @param {Object} [context]
    @param {Array} [domain]
    */
    init: function(name, context, domain) {
        this.name = name;
        this._context = context || {};
        this._domain = domain || [];
    },
    /**
     * @deprecated does not allow to specify kwargs, directly use call() instead
     */
    get_func: function (method_name) {
        var self = this;
        return function () {
            return self.call(method_name, _.toArray(arguments));
        };
    },
    /**
     * Call a method (over RPC) on the bound OpenERP model.
     *
     * @param {String} method name of the method to call
     * @param {Array} [args] positional arguments
     * @param {Object} [kwargs] keyword arguments
     * @param {Object} [options] additional options for the rpc() method
     * @returns {jQuery.Deferred<>} call result
     */
    call: function (method, args, kwargs, options) {
        args = args || [];
        kwargs = kwargs || {};
        if (!_.isArray(args)) {
            // call(method, kwargs)
            kwargs = args;
            args = [];
        }
        var call_kw = '/web/dataset/call_kw/' + this.name + '/' + method;
        return session.rpc(call_kw, {
            model: this.name,
            method: method,
            args: args,
            kwargs: kwargs
        }, options);
    },
    /**
     * Executes a signal on the designated workflow, on the bound OpenERP model
     *
     * @param {Number} id workflow identifier
     * @param {String} signal signal to trigger on the workflow
     */
    exec_workflow: function (id, signal) {
        return session.rpc('/web/dataset/exec_workflow', {
            model: this.name,
            id: id,
            signal: signal
        });
    },
    /**
     * Performs a fields_view_get and apply postprocessing.
     * return a {$.Deferred} resolved with the fvg
     *
     * @param {Object} args
     * @param {String|Object} args.model instance.web.Model instance or string repr of the model
     * @param {Object} [args.context] context if args.model is a string
     * @param {Number} [args.view_id] id of the view to be loaded, default view if null
     * @param {String} [args.view_type] type of view to be loaded if view_id is null
     * @param {Boolean} [args.toolbar=false] get the toolbar definition
     */
    fields_view_get: function (options) {

        return this.call('fields_view_get', {
            view_id: options.view_id,
            view_type: options.view_type,
            context: options.context,
            toolbar: options.toolbar || false
        }).then(function postprocess(fvg) {
            var doc = $.parseXML(fvg.arch).documentElement;
            fvg.arch = utils.xml_to_json(doc, (doc.nodeName.toLowerCase() !== 'kanban'));
            if ('id' in fvg.fields) {
                // Special case for id's
                var id_field = fvg.fields.id;
                id_field.original_type = id_field.type;
                id_field.type = 'id';
            }
            _.each(fvg.fields, function(field) {
                _.each(field.views || {}, function(view) {
                    postprocess(view);
                });
            });
            return fvg;
        });
    }
});

return Model;
});
