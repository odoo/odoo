
var _gaq = _gaq || [];  // asynchronous stack used by google analytics

openerp.web_analytics = function(instance) {

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
        ga.src   = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
        var s = document.getElementsByTagName('script')[0];
        s.parentNode.insertBefore(ga,s);
    })();

    instance.web_analytics.Tracker = instance.web.Class.extend({
        /*
        *  This method initializes the tracker
        */
        init: function() {
            /* Comment this lines when going on production, only used for testing on localhost
            _gaq.push(['_setAccount', 'UA-35793871-1']);
            _gaq.push(['_setDomainName', 'none']);
            */

            /* Uncomment this lines when going on production */
            _gaq.push(['_setAccount', 'UA-7333765-1']);
            _gaq.push(['_setDomainName', '.openerp.com']);  // Allow multi-domain
            /**/
        },
        /*
        * This method MUST be overriden by saas_demo and saas_trial in order to
        * set the correct user type. By default, the user connected is local to the DB.
        */
        _get_user_type: function() {
            return 'Local User';
        },
        /*
        * This method gets the user access level, to be used as CV in GA
        */
        _get_user_access_level: function() {
            if (instance.session.uid === 1) {
                return 'Admin User';
            // Make the difference between portal users and anonymous users
            } else if (instance.session.username.indexOf('@') !== -1) {
                if (instance.session.username.indexOf('anonymous') === -1) {
                    return 'Portal User';
                } else {
                    return 'Anonymous User';
                }
            } else if (instance.session.username.indexOf('anonymous') !== -1) {
                return 'Anonymous User';
            } else {
                return 'Normal User';
            }
        },
        /*
        * This method contains the initialization of all user-related custom variables
        * stored in GA. Also other modules can override it to add new custom variables
        */
        initialize_custom: function() {
            // Track User Access Level, Custom Variable 4 in GA with visitor level scope
            // Values: 'Admin User', 'Normal User', 'Portal User', 'Anonymous User'
            _gaq.push(['_setCustomVar', 4, 'User Access Level', this.user_access_level, 1]);

            // Track User Type Conversion, Custom Variable 3 in GA with session level scope
            // Values: 'Visitor', 'Demo', 'Online Trial', 'Online Paying', 'Local User'
            _gaq.push(['_setCustomVar', 1, 'User Type Conversion', this._get_user_type(), 2]);

            return instance.session.rpc("/web/webclient/version_info", {})
                .done(function(res) {
                    _gaq.push(['_setCustomVar', 5, 'Version', res.server_version, 3]);
                    return;
                });
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
                var url = instance.web_analytics.generateUrl({'model': state.model, 'view_type': state.view_type});
                this._push_event({
                    'category': state.model,
                    'action': state.view_type,
                    'label': url,
                });
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
            instance.web.FormView.include({
                init: function(parent, dataset, view_id, options) {
                    this._super.apply(this, arguments);
                    var self = this;
                    this.on('record_created', self, function(r) {
                        var url = instance.web_analytics.generateUrl({'model': r.model, 'view_type': 'form'});
                        t._push_event({
                            'category': r.model,
                            'action': 'form',
                            'label': url,
                        });
                    });
                    this.on('record_saved', self, function(r) {
                        var url = instance.web_analytics.generateUrl({'model': r.model, 'view_type': 'form'});
                        t._push_event({
                            'category': r.model,
                            'action': 'form',
                            'label': url,
                        });
                    });
                }
            });

            // Track client actions
            instance.web.ActionManager.include({
                ir_actions_client: function (action, options) {
                    var url = instance.web_analytics.generateUrl({'action': action.tag});
                    var category = action.res_model || action.type;
                    t._push_event({
                        'category': action.res_model || action.type,
                        'action': action.name || action.tag,
                        'label': url,
                    });
                    return this._super.apply(this, arguments);
                },
            });

            // Track button events
            instance.web.View.include({
                do_execute_action: function(action_data, dataset, record_id, on_closed) {
                    var category = this.model || dataset.model || '';
                    var action;
                    if (action_data.name && _.isNaN(action_data.name-0)) {
                        action = action_data.name;
                    } else {
                        action = action_data.string || action_data.special || '';
                    }
                    var url = instance.web_analytics.generateUrl({'model': category, 'view_type': this.view_type});
                    t._push_event({
                        'category': category,
                        'action': action,
                        'label': url,
                    });
                    return this._super.apply(this, arguments);
                },
            });

            // Track error events
            instance.web.CrashManager.include({
                show_error: function(error) {
                    var hash = window.location.hash;
                    var params = $.deparam(hash.substr(hash.indexOf('#')+1));
                    var options = {};
                    if (params.model && params.view_type) {
                        options = {'model': params.model, 'view_type': params.view_type};
                    } else {
                        options = {'action': params.action};
                    }
                    var url = instance.web_analytics.generateUrl(options);
                    if (error.code) {
                        t._push_event({
                            'category': error.message,
                            'action': error.data.fault_code,
                            'label': url,
                            'noninteraction': true,
                        });
                    } else {
                        t._push_event({
                            'category': error.type,
                            'action': error.data.debug,
                            'label': url,
                            'noninteraction': true,
                        });
                    }
                    this._super.apply(this, arguments);
                },
            });
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
                trans_data.state
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
    });

    // ----------------------------------------------------------------
    // utility functions
    // ----------------------------------------------------------------

    instance.web_analytics.generateUrl = function(options) {
        var url = '';
        _.each(options, function(value, key) {
            url += '/' + key + '=' + value;
        });
        return url;
    };

    instance.web_analytics.setupTracker = function(wc) {
        var t = wc.tracker;
        return $.when(t._get_user_access_level()).then(function(r) {
            t.user_access_level = r;
            t.initialize_custom().then(function() {
                wc.on('state_pushed', wc, t.on_state_pushed);
                t.include_tracker();
            });
        });
    };

    // Set correctly the tracker in the current instance
    if (instance.client instanceof instance.web.WebClient) {        // not for embedded clients
        instance.webclient.tracker = new instance.web_analytics.Tracker();
        instance.web_analytics.setupTracker(instance.webclient);
    } else if (!instance.client) {
        // client does not already exists, we are in monodb mode
        instance.web.WebClient.include({
            start: function() {
                var d = this._super.apply(this, arguments);
                this.tracker = new instance.web_analytics.Tracker();
                return d;
            },
            show_application: function() {
                var self = this;
                instance.web_analytics.setupTracker(self).always(function() {
                    self._super();
                });
            },
        });
    }

};
