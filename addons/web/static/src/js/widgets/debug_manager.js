odoo.define('web.DebugManager', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var dialogs = require('web.view_dialogs');
var core = require('web.core');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var framework = require('web.framework');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var utils = require('web.utils');
var ViewManager = require('web.ViewManager');
var WebClient = require('web.WebClient');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

/**
 * DebugManager base + general features (applicable to any context)
 */
var DebugManager = Widget.extend({
    template: "WebClient.DebugManager",
    events: {
        "click a[data-action]": "perform_callback",
        "mouseover .o_debug_dropdowns > li:not(.open)": function(e) {
            // Open other dropdowns on mouseover
            var $opened = this.$('.o_debug_dropdowns > li.open');
            if($opened.length) {
                $opened.removeClass('open');
                $(e.currentTarget).addClass('open').find('> a').focus();
            }
        },
    },
    init: function () {
        this._super.apply(this, arguments);
        // 15 fps, only actually call after sequences of queries
        this._update_stats = _.throttle(
            this._update_stats.bind(this),
            1000/15, {leading: false});
        this._events = null;
        if (document.querySelector('meta[name=debug]')) {
            this._events = [];
        }
    },
    start: function () {
        core.bus.on('rpc:result', this, function (req, resp) {
            this._debug_events(resp.debug);
        });
        this.on('update-stats', this, this._update_stats);
        var init;
        if ((init = document.querySelector('meta[name=debug]'))) {
            this._debug_events(JSON.parse(init.getAttribute('value')));
        }

        this.$dropdown = this.$(".o_debug_dropdown");
        // falsy if can't write to user or couldn't find technical features
        // group, otherwise features group id
        this._features_group = null;
        // whether group is currently enabled for current user
        this._has_features = false;
        // whether the current user is an administrator
        this._is_admin = session.is_system;
        return $.when(
            this._rpc({
                    model: 'res.users',
                    method: 'check_access_rights',
                    kwargs: {operation: 'write', raise_exception: false},
                }),
            session.user_has_group('base.group_no_one'),
            this._rpc({
                    model: 'ir.model.data',
                    method: 'xmlid_to_res_id',
                    kwargs: {xmlid: 'base.group_no_one'},
                }),
            this._super()
        ).then(function (can_write_user, has_group_no_one, group_no_one_id) {
            this._features_group = can_write_user && group_no_one_id;
            this._has_features = has_group_no_one;
            return this.update();
        }.bind(this));
    },
    leave_debug_mode: function () {
        var qs = $.deparam.querystring();
        delete qs.debug;
        window.location.search = '?' + $.param(qs);
    }, /**
     * Calls the appropriate callback when clicking on a Debug option
     */
    perform_callback: function (evt) {
        evt.preventDefault();
        var params = $(evt.target).data();
        var callback = params.action;

        if (callback && this[callback]) {
            // Perform the callback corresponding to the option
            this[callback](params, evt);
        } else {
            console.warn("No handler for ", callback);
        }
    },

    _debug_events: function (events) {
        if (!this._events) { return; }
        if (events && events.length) {
            this._events.push(events);
        }
        this.trigger('update-stats', this._events);
    },
    requests_clear: function () {
        if (!this._events) { return; }
        this._events = [];
        this.trigger('update-stats', this._events);
    },
    _update_stats: function (rqs) {
        var requests = 0, rtime = 0, queries = 0, qtime = 0;
        for(var r = 0; r < rqs.length; ++r) {
            for (var i = 0; i < rqs[r].length; i++) {
                var event = rqs[r][i];
                var query_start, request_start;
                switch (event[0]) {
                case 'request-start':
                    request_start = event[3] * 1e3;
                    break;
                case 'request-end':
                    ++requests;
                    rtime += (event[3] * 1e3 - request_start) | 0;
                    break;
                case 'sql-start':
                    query_start = event[3] * 1e3;
                    break;
                case 'sql-end':
                    ++queries;
                    qtime += (event[3] * 1e3 - query_start) | 0;
                    break;
                }
            }
        }
        this.$('#debugmanager_requests_stats').text(
            _.str.sprintf(_t("%d requests (%d ms) %d queries (%d ms)"),
            requests, rtime, queries, qtime));
    },
    show_timelines: function () {
        if (this._overlay) {
            this._overlay.destroy();
            this._overlay = null;
            return;
        }
        this._overlay = new RequestsOverlay(this);
        this._overlay.appendTo(document.body);
    },

    /**
     * Update the debug manager: reinserts all "universal" controls
     */
    update: function () {
        this.$dropdown
            .empty()
            .append(QWeb.render('WebClient.DebugManager.Global', {
                manager: this,
            }));
        return $.when();
    },
    select_view: function () {
        var self = this;
        new dialogs.SelectCreateDialog(this, {
            res_model: 'ir.ui.view',
            title: _t('Select a view'),
            disable_multiple_selection: true,
            on_selected: function (element_ids) {
                self._rpc({
                        model: 'ir.ui.view',
                        method: 'search_read',
                        domain: [['id', '=', element_ids[0]]],
                        fields: ['name', 'model', 'type'],
                        limit: 1,
                    })
                    .then(function (views) {
                        var view = views[0];
                        self.do_action({
                            type: 'ir.actions.act_window',
                            name: view.name,
                            res_model: view.model,
                            views: [[view.id, view.type]]
                        });
                    });
            }
        }).open();
    },
    perform_js_tests: function () {
        this.do_action({
            name: _t("JS Tests"),
            target: 'new',
            type: 'ir.actions.act_url',
            url: '/web/tests?mod=*'
        });
    },
    split_assets: function() {
        window.location = $.param.querystring(window.location.href, 'debug=assets');
    },
});

/**
 * DebugManager features depending on having an action, and possibly a model
 * (window action)
 */
DebugManager.include({
    /**
     * Updates current action (action descriptor) on tag = action,
     */
    update: function (tag, descriptor) {
        if (tag === 'action') {
            this._action = descriptor;
        }
        return this._super().then(function () {
            this.$dropdown.find(".o_debug_leave_section").before(QWeb.render('WebClient.DebugManager.Action', {
                manager: this,
                action: this._action
            }));
        }.bind(this));
    },
    edit: function (params, evt) {
        this.do_action({
            res_model: params.model,
            res_id: params.id,
            name: evt.target.text,
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
            view_mode: 'form',
            target: 'new',
            flags: {action_buttons: true, headless: true}
        });
    },
    get_view_fields: function () {
        var self = this;
        var model = this._action.res_model;
        this._rpc({
                model: model,
                method: 'fields_get',
                kwargs: {
                    attributes: ['string', 'searchable', 'required', 'readonly', 'type', 'store', 'sortable', 'relation', 'help']
                },
            })
            .done(function (fields) {
                new Dialog(self, {
                    title: _.str.sprintf(_t("Fields of %s"), model),
                    $content: $(QWeb.render('WebClient.DebugManager.Action.Fields', {
                        fields: fields
                    }))
                }).open();
            });
    },
    manage_filters: function () {
        this.do_action({
            res_model: 'ir.filters',
            name: _t('Manage Filters'),
            views: [[false, 'list'], [false, 'form']],
            type: 'ir.actions.act_window',
            context: {
                search_default_my_filters: true,
                search_default_model_id: this._action.res_model
            }
        });
    },
    translate: function() {
        this._rpc({
                model: 'ir.translation',
                method: 'get_technical_translations',
                args: [this._action.res_model],
            })
            .then(this.do_action);
    }
});

/**
 * DebugManager features depending on having a form view or single record.
 * These could theoretically be split, but for now they'll be considered one
 * and the same.
 */
DebugManager.include({
    start: function () {
        this._can_edit_views = false;
        return $.when(
            this._super(),
            this._rpc({
                    model: 'ir.ui.view',
                    method: 'check_access_rights',
                    kwargs: {operation: 'write', raise_exception: false},
                })
                .then(function (ar) {
                    this._can_edit_views = ar;
                }.bind(this))
        );
    },
    update: function (tag, descriptor, widget) {
        switch (tag) {
        case 'action':
            if (this._view_manager) {
                this._view_manager.off('switch_mode', this);
            }
            if (!(widget instanceof ViewManager)) {
                this._active_view = null;
                this._view_manager = null;
                break;
            }
            this._view_manager = widget;
            widget.on('switch_mode', this, function () {
                this.update('view', null, widget);
            });
        case 'view':
            this._active_view = widget.active_view;
        }

        return this._super(tag, descriptor).then(function () {
            this.$dropdown.find(".o_debug_leave_section").before(QWeb.render('WebClient.DebugManager.View', {
                manager: this,
                action: this._action,
                view: this._active_view,
                can_edit: this._can_edit_views,
                searchview: this._view_manager && this._view_manager.searchview,
            }));
        }.bind(this));
    },

    get_metadata: function() {
        var ds = this._view_manager.dataset;
        if (!this._active_view.controller.getSelectedIds().length) {
            console.warn(_t("No metadata available"));
            return;
        }
        ds.call('get_metadata', [this._active_view.controller.getSelectedIds()]).done(function(result) {
            var metadata = result[0];
            metadata.creator = field_utils.format.many2one(metadata.create_uid);
            metadata.lastModifiedBy = field_utils.format.many2one(metadata.write_uid);
            var createDate = field_utils.parse.datetime(metadata.create_date);
            metadata.create_date = field_utils.format.datetime(createDate);
            var modificationDate = field_utils.parse.datetime(metadata.write_date);
            metadata.write_date = field_utils.format.datetime(modificationDate);
            new Dialog(this, {
                title: _.str.sprintf(_t("Metadata (%s)"), ds.model),
                size: 'medium',
                $content: QWeb.render('WebClient.DebugViewLog', {
                    perm : metadata,
                })
            }).open();
        });
    },
    set_defaults: function() {
        this._active_view.controller.open_defaults_dialog();
    },
    fvg: function() {
        var dialog = new Dialog(this, { title: _t("Fields View Get") }).open();
        $('<pre>').text(utils.json_node_to_xml(
            this._active_view.controller.renderer.arch, true)
        ).appendTo(dialog.$el);
    },
    print_workflow: function() {
        var ids = this._active_view.controller.getSelectedIds();
        framework.blockUI();
        var action = {
            context: { active_ids: ids },
            report_name: "workflow.instance.graph",
            datas: {
                model: this._view_manager.dataset.model,
                id: ids[0],
                nested: true,
            }
        };
        session.get_file({
            url: '/web/report',
            data: {action: JSON.stringify(action)},
            complete: framework.unblockUI
        });
    },
});
function make_context(width, height, fn) {
    var canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    // make e.layerX/e.layerY imitate e.offsetX/e.offsetY.
    canvas.style.position = 'relative';
    var ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.mozImageSmoothingEnabled = false;
    ctx.oImageSmoothingEnabled = false;
    ctx.webkitImageSmoothingEnabled = false;
    fn && fn(ctx);
    return ctx;
}
var RequestsOverlay = Widget.extend({
    template: 'WebClient.DebugManager.RequestsOverlay',
    TRACKS: 8,
    TRACK_WIDTH: 9,
    events: {
        mousemove: function (e) {
            this.$tooltip.hide();
        }
    },
    init: function () {
        this._super.apply(this, arguments);
        this._render = _.throttle(
            this._render.bind(this),
            1000/15, {leading: false}
        );
    },
    start: function () {
        var _super = this._super();
        this.$tooltip = this.$('div.o_debug_tooltip');
        this.getParent().on('update-stats', this, this._render);
        this._render();
        return _super;
    },
    tooltip: function (text, start, end, x, y) {
        // x and y are hit point with respect to the viewport. To know where
        // this hit point is with respect to the overlay, subtract the offset
        // between viewport and overlay, then add scroll factor of overlay
        // (which isn't taken in account by the viewport).
        //
        // Normally the viewport overlay should sum offsets of all
        // offsetParents until we reach `null` but in this case the overlay
        // should have been added directly to the body, which should have an
        // offset of 0.

        var top = y - this.el.offsetTop + this.el.scrollTop + 1;
        var left = x - this.el.offsetLeft + this.el.scrollLeft + 1;
        this.$tooltip.css({top: top, left: left}).show()[0].innerHTML = ['<p>', text, ' (', (end - start), 'ms)', '</p>'].join('');
    },

    _render: function () {
        var $summary = this.$('header'),
            w = $summary[0].clientWidth,
            $requests = this.$('.o_debug_requests');
        $summary.find('canvas').attr('width', w);
        var tracks = document.getElementById('o_debug_requests_summary');

        _.invoke(this.getChildren(), 'destroy');

        var requests = this.getParent()._events;
        var bounds = this._get_bounds(requests);
        // horizontal scaling factor for summary
        var scale = w / (bounds.high - bounds.low);

        // store end-time of "current" requests, to find out which track a
        // request should go in, just look for the first track whose end-time
        // is smaller than the new request's start time.
        var track_ends = _(this.TRACKS).times(_.constant(-Infinity));

        var ctx = tracks.getContext('2d');
        ctx.lineWidth = this.TRACK_WIDTH;
        for (var i = 0; i < requests.length; i++) {
            var request = requests[i];
            // FIXME: is it certain that events in the request are sorted by timestamp?
            var rstart = Math.floor(request[0][3] * 1e3);
            var rend = Math.ceil(request[request.length - 1][3] * 1e3);
            // find free track for current request
            for(var track=0; track < track_ends.length; ++track) {
                if (track_ends[track] < rstart) { break; }
            }
            // FIXME: display error message of some sort? Re-render with larger area? Something?
            if (track >= track_ends.length) {
                console.warn("could not find an empty summary track");
                continue;
            }
            // set new track end
            track_ends[track] = rend;
            ctx.save();
            ctx.translate(Math.floor((rstart - bounds.low) * scale), track * (this.TRACK_WIDTH + 1));
            this._draw_request(request, ctx, 0, scale);
            ctx.restore();
            new RequestDetails(this, request, scale).appendTo($requests);
        }
    },
    _draw_request: function (request, to_context, step, hscale, handle_event) {
        // have one draw surface for each event type:
        // * no need to alter context from one event to the next, each surface
        //   gets its own color for all its lifetime
        // * surfaces can be blended in a specified order, which means events
        //   can be drawn in any order, no need to care about z-index while
        //   serializing events to the surfaces
        var surfaces = {
            request: make_context(to_context.canvas.width, to_context.canvas.height, function (ctx) {
                ctx.strokeStyle = 'blue';
                ctx.fillStyle = '#88f';
                ctx.lineJoin = 'round';
                ctx.lineWidth = 1;
            }),
            //func: make_context(to_context.canvas.width, to_context.canvas.height, function (ctx) {
            //    ctx.strokeStyle = 'gray';
            //    ctx.lineWidth = to_context.lineWidth;
            //    ctx.translate(0, initial_offset);
            //}),
            sql: make_context(to_context.canvas.width, to_context.canvas.height, function (ctx) {
                ctx.strokeStyle = 'red';
                ctx.fillStyle = '#f88';
                ctx.lineJoin = 'round';
                ctx.lineWidth = 1;
            }),
            template: make_context(to_context.canvas.width, to_context.canvas.height, function (ctx) {
                ctx.strokeStyle = 'green';
                ctx.fillStyle = '#8f8';
                ctx.lineJoin = 'round';
                ctx.lineWidth = 1;
            })
        };
        // apply scaling manually so zooming in improves display precision
        var stacks = {}, start = Math.floor(request[0][3] * 1e3 * hscale);
        var event_idx = 0;

        var rect_width = to_context.lineWidth;
        for (var i = 0; i < request.length; i++) {
            var type, m, event = request[i];
            var tag = event[0], timestamp = Math.floor(event[3] * 1e3 * hscale) - start;

            if (m = /(\w+)-start/.exec(tag)) {
                type = m[1];
                if (!(type in stacks)) { stacks[type] = []; }
                handle_event && handle_event(event_idx, timestamp, event);
                stacks[type].push({
                    timestamp: timestamp,
                    idx: event_idx++
                });
            } else if (m = /(\w+)-end/.exec(tag)) {
                type = m[1];
                var stack = stacks[type];
                var estart = stack.pop(), duration = Math.ceil(timestamp - estart.timestamp);
                handle_event && handle_event(estart.idx, timestamp, event);

                var surface = surfaces[type];
                if (!surface) { continue; } // FIXME: support for unknown event types

                var y = step * estart.idx;
                // path rectangle for the current event on the relevant surface
                surface.rect(estart.timestamp + 0.5, y + 0.5, duration || 1, rect_width);
            }
        }
        // add each layer to the main canvas
        var keys = ['request', /*'func', */'template', 'sql'];
        for (var j = 0; j < keys.length; ++j) {
            // stroke and fill all rectangles for the relevant surface/context
            var ctx = surfaces[keys[j]];
            ctx.fill();
            ctx.stroke();
            to_context.drawImage(ctx.canvas, 0, 0);
        }
    },
    /**
     * Returns first and last events in milliseconds
     *
     * @param requests
     * @returns {{low: number, high: number}}
     * @private
     */
    _get_bounds: function (requests) {
        var low = +Infinity;
        var high =-+Infinity;

        for (var i = 0; i < requests.length; i++) {
            var request = requests[i];
            for (var j = 0; j < request.length; j++) {
                var event = request[j];
                var timestamp = event[3];
                low = Math.min(low, timestamp);
                high = Math.max(high, timestamp);
            }
        }
        return {low: Math.floor(low * 1e3), high: Math.ceil(high * 1e3)};
    }
});
var RequestDetails = Widget.extend({
    events: {
        click: function () {
            this._open = !this._open;
            this.render();
        },
        'mousemove canvas': function (e) {
            e.stopPropagation();
            var y = e.y || e.offsetY || e.layerY;
            if (!y) { return; }
            var event = this._payloads[Math.floor(y / this._REQ_HEIGHT)];
            if (!event) { return; }

            this.getParent().tooltip(event.payload, event.start, event.stop, e.clientX, e.clientY);
        }
    },
    init: function (parent, request, scale) {
        this._super.apply(this, arguments);
        this._request = request;
        this._open = false;
        this._scale = scale;
        this._REQ_HEIGHT = 20;
    },
    start: function () {
        this.el.style.borderBottom = '1px solid black';
        this.render();
        return this._super();
    },
    render: function () {
        var request_cell_height = this._REQ_HEIGHT, TITLE_WIDTH = 200;
        var request = this._request;
        var req_start = request[0][3] * 1e3;
        var req_duration = request[request.length - 1][3] * 1e3 - req_start;
        var height = request_cell_height * (this._open ? request.length / 2 : 1);
        var cell_center = request_cell_height / 2;
        var ctx = make_context(210 + Math.ceil(req_duration * this._scale), height, function (ctx) {
            ctx.lineWidth = cell_center;
        });
        this.$el.empty().append(ctx.canvas);
        var payloads = this._payloads = [];

        // lazy version: if the render is single-line (!this._open), the extra
        // content will be discarded when the text canvas gets pasted onto the
        // main canvas. An improvement would be to not do text rendering
        // beyond the first event for "closed" requests events… then again
        // that makes for more regular rendering profile?
        var text_ctx = make_context(TITLE_WIDTH, height, function (ctx) {
            ctx.font = '12px sans-serif';
            ctx.textAlign = 'right';
            ctx.textBaseline = 'middle';
            ctx.translate(0, cell_center);
        });

        ctx.save();
        ctx.translate(TITLE_WIDTH + 10, ((request_cell_height/4)|0));

        this.getParent()._draw_request(request, ctx, this._open ? request_cell_height : 0, this._scale, function (idx, timestamp, event) {
            if (/-start$/g.test(event[0])) {
                payloads.push({
                    payload: event[2],
                    start: timestamp,
                    stop: null
                });

                // we want ~200px wide, assume the average character is at
                // least 4px wide => there can be *at most* 49 characters
                var title = event[2];
                title = title.replace(/\s+$/, '');
                title = title.length <= 50 ? title : ('…' + title.slice(-49));
                while (text_ctx.measureText(title).width > 200) {
                    title = '…' + title.slice(2);
                }
                text_ctx.fillText(title, TITLE_WIDTH, request_cell_height * idx);
            } else if (/-end$/g.test(event[0])) {
                payloads[idx].stop = timestamp;
            }
        });
        ctx.restore();
        // add the text layer to the main canvas
        ctx.drawImage(text_ctx.canvas, 0, 0);
    }
});

if (core.debug) {
    SystrayMenu.Items.push(DebugManager);

    WebClient.include({
        current_action_updated: function(action) {
            this._super.apply(this, arguments);
            var action_descr = action && action.action_descr;
            var action_widget = action && action.widget;
            var debug_manager = _.find(this.systray_menu.widgets, function(item) {return item instanceof DebugManager; });
            debug_manager.update('action', action_descr, action_widget);
        },
    });

    Dialog.include({
        open: function() {
            var self = this;

            var parent = self.getParent();
            if (parent instanceof ActionManager && parent.dialog_widget) {
                // Instantiate the DebugManager and insert it into the DOM once dialog is opened
                this.opened(function() {
                    self.debug_manager = new DebugManager(self);
                    var $header = self.$modal.find('.modal-header');
                    return self.debug_manager.prependTo($header).then(function() {
                        self.debug_manager.update('action', parent.dialog_widget.action, parent.dialog_widget);
                    });
                });
            }

            return this._super.apply(this, arguments);
        },
    });
}

return DebugManager;

});
