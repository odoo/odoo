
var _gaq = _gaq || [];  // asynchronous stack used by google analytics

odoo.define('web_analytics.web_analytics', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var CrashManager = require('web.CrashManager');
var core = require('web.core');
var FormView = require('web.FormView');
var Session = require('web.Session');
var session = require('web.session');
var View = require('web.View');
var web_client = require('web.web_client');
var WebClient = require('web.WebClient');

/*
*  The Web Analytics Module inserts the Google Analytics JS Snippet
*  at the top of the page, and sends to google an url each time the
*  openerp url is changed.
*  The pushes of the urls is made by triggering the 'state_pushed' event in the
*  web_client.do_push_state() method which is responsible of changing the openerp current url
*/

// Google Analytics Code snippet
(function() {
    var ga   = document.createElement('script');
    ga.type  = 'text/javascript';
    ga.async = true;
    ga.src   = ('https:' === document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0];
    s.parentNode.insertBefore(ga,s);
})();

var Tracker = core.Class.extend({
    /*
    * This method initializes the tracker
    */
    init: function(webclient) {
        var self = this;
        self.initialized = $.Deferred();
        _gaq.push(['_setAccount', 'UA-7333765-1']);
        _gaq.push(['_setDomainName', '.openerp.com']);  // Allow multi-domain
        self.initialize_custom(webclient).then(function() {
            webclient.on('state_pushed', self, self.on_state_pushed);
            self.include_tracker();
        });
    },
    /*
    * This method MUST be overriden by saas_demo and saas_trial in order to
    * set the correct user type. By default, the user connected is local to
    * the DB (like in accounts).
    */
    _get_user_type: function() {
        return 'Local User';
    },
    /*
    * This method gets the user access level, to be used as CV in GA
    */
    _get_user_access_level: function() {
        if (!session.session_is_valid()) {
            return "Unauthenticated User";
        }
        if (session.uid === 1) {
            return 'Admin User';
        }
        // Make the difference between portal users and anonymous users
        if (session.username.indexOf('@') !== -1) {
            return 'Portal User';
        }
        if (session.username === 'anonymous') {
            return 'Anonymous User';
        }
        return 'Normal User';
    },
    
    /*
    * This method contains the initialization of all user-related custom variables
    * stored in GA. Also other modules can override it to add new custom variables
    * Must be followed by a call to _push_*() in order to actually send the data
    * to GA.
    */
    initialize_custom: function() {
        var self = this;
        session.rpc("/web/webclient/version_info", {})
            .done(function(res) {
                _gaq.push(['_setCustomVar', 5, 'Version', res.server_version, 3]);
                self._push_customvars();
                self.initialized.resolve(self);
            });
        return self.initialized;
    },

    /*
     * Method called in order to send _setCustomVar to GA
     */
    _push_customvars: function() {
        var self = this;
        // Track User Access Level, Custom Variable 4 in GA with visitor level scope
        // Values: 'Admin User', 'Normal User', 'Portal User', 'Anonymous User'
        _gaq.push(['_setCustomVar', 4, 'User Access Level', self._get_user_access_level(), 1]);

        // Track User Type Conversion, Custom Variable 3 in GA with session level scope
        // Values: 'Visitor', 'Demo', 'Online Trial', 'Online Paying', 'Local User'
        _gaq.push(['_setCustomVar', 1, 'User Type Conversion', self._get_user_type(), 2]);
    },
    
    /*
    * Method called in order to send _trackPageview to GA
    */
    _push_pageview: function(url) {
        _gaq.push(['_trackPageview', url]);
    },
    /*
    * Method called in order to send _trackEvent to GA
    */
    _push_event: function(options) {
        _gaq.push(['_trackEvent',
            options.category,
            options.action,
            options.label,
            options.value,
            options.noninteraction
        ]);
    },
    /*
    * Method called in order to send ecommerce transactions to GA
    */
    _push_ecommerce: function(trans_data, item_list) {
        _gaq.push(['_addTrans',
            trans_data.order_id,
            trans_data.store_name,
            trans_data.total,
            trans_data.tax,
            trans_data.shipping,
            trans_data.city,
            trans_data.state,
            trans_data.country,
        ]);
        _.each(item_list, function(item) {
            _gaq.push(['_addItem',
                item.order_id,
                item.sku,
                item.name,
                item.category,
                item.price,
                item.quantity,
            ]);
        });
        _gaq.push(['_trackTrans']);
    },
    /*
    *  This method contains the initialization of the object and view type
    *  as an event in GA.
    */
    on_state_pushed: function(state) {
        // Track only pages corresponding to a 'normal' view of OpenERP, views
        // related to client actions are tracked by the action manager
        if (state.model && state.view_type) {
            // Track the page
            var url = generateUrl({'model': state.model, 'view_type': state.view_type});
            this._push_event({
                'category': state.model,
                'action': state.view_type,
                'label': url,
            });
            this._push_pageview(url);
        }
    },
    /*
    * This method includes the tracker into views and managers. It can be overriden
    * by other modules in order to extend tracking functionalities
    */
    include_tracker: function() {
        var t = this;
        // Track the events related with the creation and the  modification of records,
        // the view type is always form
        FormView.include({
            init: function(parent, dataset, view_id, options) {
                this._super.apply(this, arguments);
                var self = this;
                this.on('record_created', self, function(r) {
                    var url = generateUrl({'model': self.model, 'view_type': 'form'});
                    t._push_event({
                        'category': self.model,
                        'action': 'create',
                        'label': url,
                        'noninteraction': true,
                    });
                });
                this.on('record_saved', self, function(r) {
                    var url = generateUrl({'model': self.model, 'view_type': 'form'});
                    t._push_event({
                        'category': self.model,
                        'action': 'save',
                        'label': url,
                        'noninteraction': true,
                    });
                });
            }
        });

        // Track client actions
        ActionManager.include({
            ir_actions_client: function (action, options) {
                var url = generateUrl({'action': action.tag});
                t._push_event({
                    'category': action.type,
                    'action': action.tag,
                    'label': url,
                });
                t._push_pageview(url);
                return this._super.apply(this, arguments);
            },
        });

        // Track button events
        View.include({
            do_execute_action: function(action_data, dataset, record_id, on_closed) {
                var category = this.model || dataset.model || '';
                var action;
                if (action_data.name && _.isNaN(action_data.name-0)) {
                    action = action_data.name;
                } else {
                    action = action_data.string || action_data.special || '';
                }
                var url = generateUrl({'model': category, 'view_type': this.view_type});
                t._push_event({
                    'category': category,
                    'action': action,
                    'label': url,
                    'noninteraction': true,
                });
                return this._super.apply(this, arguments);
            },
        });

        // Track error events
        CrashManager.include({
            show_error: function(error) {
                var hash = window.location.hash;
                var params = $.deparam(hash.substr(hash.indexOf('#')+1));
                var options = {};
                if (params.model && params.view_type) {
                    options = {'model': params.model, 'view_type': params.view_type};
                } else {
                    options = {'action': params.action};
                }
                var url = generateUrl(options);
                t._push_event({
                    'category': options.model || "ir.actions.client",
                    'action': "error " + (error.code ? error.message + error.data.message : error.type + error.data.debug),
                    'label': url,
                    'noninteraction': true,
                });
                this._super.apply(this, arguments);
            },
        });
    },
});

// ----------------------------------------------------------------
// utility functions
// ----------------------------------------------------------------

var generateUrl = function(options) {
    var url = '';
    var keys = _.keys(options);
    keys = _.sortBy(keys, function(i) { return i;});
    _.each(keys, function(key) {
        url += '/' + key + '/' + options[key];
    });
    return url;
};

// kept for API compatibility
var setupTracker = function(wc) {
    return wc.tracker.initialized;
};

WebClient.include({
    bind_events: function() {
        this._super.apply(this, arguments);
        this.tracker = new Tracker(this);
    },
});

Session.include({
    session_authenticate: function() {
        return $.when(this._super.apply(this, arguments)).then(function() {
            web_client.tracker._push_customvars();
        });
    },
});
 
});
