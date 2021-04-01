odoo.define('web.DebugManager.Backend', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var DebugManager = require('web.DebugManager');
var dialogs = require('web.view_dialogs');
var startClickEverywhere = require('web.clickEverywhere');
var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var SystrayMenu = require('web.SystrayMenu');
var utils = require('web.utils');
var WebClient = require('web.WebClient');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

/**
 * DebugManager features depending on backend
 */
DebugManager.include({
    requests_clear: function () {
        if (!this._events) {
            return;
        }
        this._events = [];
        this.trigger('update-stats', this._events);
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
     * Updates current action (action descriptor) on tag = action,
     */
    update: function (tag, descriptor) {
        return this._super().then(function () {
            this.$dropdown.find(".o_debug_split_assets").before(QWeb.render('WebClient.DebugManager.Backend', {
                manager: this,
            }));
        }.bind(this));
    },
    select_view: function () {
        var self = this;
        new dialogs.SelectCreateDialog(this, {
            res_model: 'ir.ui.view',
            title: _t('Select a view'),
            disable_multiple_selection: true,
            domain: [['type', '!=', 'qweb'], ['type', '!=', 'search']],
            on_selected: function (records) {
                self._rpc({
                        model: 'ir.ui.view',
                        method: 'search_read',
                        domain: [['id', '=', records[0].id]],
                        fields: ['name', 'model', 'type'],
                        limit: 1,
                    })
                    .then(function (views) {
                        var view = views[0];
                        view.type = view.type === 'tree' ? 'list' : view.type; // ignore tree view
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
    /**
     * Runs the JS (desktop) tests
     */
    perform_js_tests: function () {
        this.do_action({
            name: _t("JS Tests"),
            target: 'new',
            type: 'ir.actions.act_url',
            url: '/web/tests?mod=*'
        });
    },
    /**
     * Runs the JS mobile tests
     */
    perform_js_mobile_tests: function () {
        this.do_action({
            name: _t("JS Mobile Tests"),
            target: 'new',
            type: 'ir.actions.act_url',
            url: '/web/tests/mobile?mod=*'
        });
    },
    perform_click_everywhere_test: function () {
        var $homeMenu = $("nav.o_main_navbar > a.o_menu_toggle.fa-th");
        $homeMenu.click();
        startClickEverywhere();
    },
});

/**
 * DebugManager features depending on having an action, and possibly a model
 * (window action)
 */
DebugManager.include({
    async start() {
        const [_, canSeeRecordRules, canSeeModelAccess] = await Promise.all([
            this._super(...arguments),
            this._checkAccessRight('ir.rule', 'read'),
            this._checkAccessRight('ir.model.access', 'read'),
        ])
        this.canSeeRecordRules = canSeeRecordRules;
        this.canSeeModelAccess = canSeeModelAccess;
    },
    /**
     * Return the ir.model id from the model name
     * @param {string} modelName
     */
    async getModelId(modelName) {
        const [modelId] = await this._rpc({
            model: 'ir.model',
            method: 'search',
            args: [[['model', '=', modelName]]],
            kwargs: { limit: 1},
        });
        return modelId
    },
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
    async get_view_fields () {
        const modelId = await this.getModelId(this._action.res_model);
        this.do_action({
            res_model: 'ir.model.fields',
            name: _t('View Fields'),
            views: [[false, 'list'], [false, 'form']],
            domain: [['model_id', '=', modelId]],
            type: 'ir.actions.act_window',
            context: {
                'default_model_id': modelId
            }
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
    },
    async actionRecordRules() {
        const modelId = await this.getModelId(this._action.res_model);
        this.do_action({
            res_model: 'ir.rule',
            name: _t('Model Record Rules'),
            views: [[false, 'list'], [false, 'form']],
            domain: [['model_id', '=', modelId]],
            type: 'ir.actions.act_window',
            context: {
                'default_model_id': modelId,
            },
        });
    },
    async actionModelAccess() {
        const modelId = await this.getModelId(this._action.res_model);
        this.do_action({
            res_model: 'ir.model.access',
            name: _t('Model Access'),
            views: [[false, 'list'], [false, 'form']],
            domain: [['model_id', '=', modelId]],
            type: 'ir.actions.act_window',
            context: {
                'default_model_id': modelId,
            },
        });
    },
});

/**
 * DebugManager features depending on having a form view or single record.
 * These could theoretically be split, but for now they'll be considered one
 * and the same.
 */
DebugManager.include({
    start: function () {
        this._can_edit_views = false;
        return Promise.all([
            this._super(),
            this._checkAccessRight('ir.ui.view', 'write')
                .then(function (ar) {
                    this._can_edit_views = ar;
                }.bind(this))
            ]
        );
    },
    update: function (tag, descriptor, widget) {
        if (tag === 'action' || tag === 'view') {
            this._controller = widget;
        }
        return this._super(tag, descriptor).then(function () {
            this.$dropdown.find(".o_debug_leave_section").before(QWeb.render('WebClient.DebugManager.View', {
                action: this._action,
                can_edit: this._can_edit_views,
                controller: this._controller,
                withControlPanel: this._controller && this._controller.withControlPanel,
                manager: this,
                view: this._controller && _.findWhere(this._action.views, {
                    type: this._controller.viewType,
                }),
            }));
        }.bind(this));
    },
    get_attachments: function() {
        var selectedIDs = this._controller.getSelectedIds();
        if (!selectedIDs.length) {
            console.warn(_t("No attachment available"));
            return;
        }
        this.do_action({
            res_model: 'ir.attachment',
            name: _t('Manage Attachments'),
            views: [[false, 'list'], [false, 'form']],
            type: 'ir.actions.act_window',
            domain: [['res_model', '=', this._action.res_model], ['res_id', '=', selectedIDs[0]]],
            context: {
                default_res_model: this._action.res_model,
                default_res_id: selectedIDs[0],
            },
        });
    },
    get_metadata: function() {
        var self = this;
        var selectedIDs = this._controller.getSelectedIds();
        if (!selectedIDs.length) {
            console.warn(_t("No metadata available"));
            return;
        }
        this._rpc({
            model: this._action.res_model,
            method: 'get_metadata',
            args: [selectedIDs],
        }).then(function(result) {
            var metadata = result[0];
            metadata.creator = field_utils.format.many2one(metadata.create_uid);
            metadata.lastModifiedBy = field_utils.format.many2one(metadata.write_uid);
            var createDate = field_utils.parse.datetime(metadata.create_date);
            metadata.create_date = field_utils.format.datetime(createDate);
            var modificationDate = field_utils.parse.datetime(metadata.write_date);
            metadata.write_date = field_utils.format.datetime(modificationDate);
            var dialog = new Dialog(this, {
                title: _.str.sprintf(_t("Metadata (%s)"), self._action.res_model),
                size: 'medium',
                $content: QWeb.render('WebClient.DebugViewLog', {
                    perm : metadata,
                })
            });
            dialog.open().opened(function () {
                dialog.$el.on('click', 'a[data-action="toggle_noupdate"]', function (ev) {
                    ev.preventDefault();
                    self._rpc({
                        model: 'ir.model.data',
                        method: 'toggle_noupdate',
                        args: [self._action.res_model, metadata.id]
                    }).then(function (res) {
                        dialog.close();
                        self.get_metadata();
                    })
                });
            })
        });
    },
    set_defaults: function() {
        var self = this;

        var display = function (fieldInfo, value) {
            var displayed = value;
            if (value && fieldInfo.type === 'many2one') {
                displayed = value.data.display_name;
                value = value.data.id;
            } else if (value && fieldInfo.type === 'selection') {
                displayed = _.find(fieldInfo.selection, function (option) {
                    return option[0] === value;
                })[1];
            }
            return [value, displayed];
        };

        var renderer = this._controller.renderer;
        var state = renderer.state;
        var fields = state.fields;
        var fieldsInfo = state.fieldsInfo.form;
        var fieldNamesInView = state.getFieldNames();
        var fieldNamesOnlyOnView = ['message_attachment_count'];
        var fieldsValues = state.data;
        var modifierDatas = {};
        _.each(fieldNamesInView, function (fieldName) {
            modifierDatas[fieldName] = _.find(renderer.allModifiersData, function (modifierdata) {
                return modifierdata.node.attrs.name === fieldName;
            });
        });
        this.fields = _.chain(fieldNamesInView)
            .difference(fieldNamesOnlyOnView)
            .map(function (fieldName) {
                var modifierData = modifierDatas[fieldName];
                var invisibleOrReadOnly;
                if (modifierData) {
                    var evaluatedModifiers = modifierData.evaluatedModifiers[state.id];
                    invisibleOrReadOnly = evaluatedModifiers.invisible || evaluatedModifiers.readonly;
                }
                var fieldInfo = fields[fieldName];
                var valueDisplayed = display(fieldInfo, fieldsValues[fieldName]);
                var value = valueDisplayed[0];
                var displayed = valueDisplayed[1];
                // ignore fields which are empty, invisible, readonly, o2m
                // or m2m
                if (!value || invisibleOrReadOnly || fieldInfo.type === 'one2many' ||
                    fieldInfo.type === 'many2many' || fieldInfo.type === 'binary' ||
                    fieldsInfo[fieldName].options.isPassword || !_.isEmpty(fieldInfo.depends)) {
                    return false;
                }
                return {
                    name: fieldName,
                    string: fieldInfo.string,
                    value: value,
                    displayed: displayed,
                };
            })
            .compact()
            .sortBy(function (field) { return field.string; })
            .value();

        var conditions = _.chain(fieldNamesInView)
            .filter(function (fieldName) {
                var fieldInfo = fields[fieldName];
                return fieldInfo.change_default;
            })
            .map(function (fieldName) {
                var fieldInfo = fields[fieldName];
                var valueDisplayed = display(fieldInfo, fieldsValues[fieldName]);
                var value = valueDisplayed[0];
                var displayed = valueDisplayed[1];
                return {
                    name: fieldName,
                    string: fieldInfo.string,
                    value: value,
                    displayed: displayed,
                };
            })
            .value();
        var d = new Dialog(this, {
            title: _t("Set Default"),
            buttons: [
                {text: _t("Close"), close: true},
                {text: _t("Save default"), click: function () {
                    var $defaults = d.$el.find('#formview_default_fields');
                    var fieldToSet = $defaults.val();
                    if (!fieldToSet) {
                        $defaults.parent().addClass('o_form_invalid');
                        return;
                    }
                    var selfUser = d.$el.find('#formview_default_self').is(':checked');
                    var condition = d.$el.find('#formview_default_conditions').val();
                    var value = _.find(self.fields, function (field) {
                        return field.name === fieldToSet;
                    }).value;
                    self._rpc({
                        model: 'ir.default',
                        method: 'set',
                        args: [
                            self._action.res_model,
                            fieldToSet,
                            value,
                            selfUser,
                            true,
                            condition || false,
                        ],
                    }).then(function () { d.close(); });
                }}
            ]
        });
        d.args = {
            fields: this.fields,
            conditions: conditions,
        };
        d.template = 'FormView.set_default';
        d.open();
    },
    fvg: function() {
        var self = this;
        var dialog = new Dialog(this, { title: _t("Fields View Get") });
        dialog.opened().then(function () {
            $('<pre>').text(utils.json_node_to_xml(
                self._controller.renderer.arch, true)
            ).appendTo(dialog.$el);
        });
        dialog.open();
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

if (config.isDebug()) {
    SystrayMenu.Items.push(DebugManager);

    WebClient.include({
        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @override
         */
        current_action_updated: function (action, controller) {
            this._super.apply(this, arguments);
            this.update_debug_manager(action, controller);
        },
        update_debug_manager: function(action, controller) {
            var debugManager = _.find(this.menu.systray_menu.widgets, function(item) {
                return item instanceof DebugManager;
            });
            debugManager.update('action', action, controller && controller.widget);
        }
    });

    ActionManager.include({
        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Returns the action of the controller currently opened in a dialog,
         * i.e. a target='new' action, if any.
         *
         * @returns {Object|null}
         */
        getCurrentActionInDialog: function () {
            if (this.currentDialogController) {
                return this.actions[this.currentDialogController.actionID];
            }
            return null;
        },
        /**
         * Returns the controller currently opened in a dialog, if any.
         *
         * @returns {Object|null}
         */
        getCurrentControllerInDialog: function () {
            return this.currentDialogController;
        },
    });

    Dialog.include({
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * @override
         */
        open: function() {
            var self = this;
            // if the dialog is opened by the ActionManager, instantiate a
            // DebugManager and insert it into the DOM once the dialog is opened
            // (delay this with a setTimeout(0) to ensure that the internal
            // state, i.e. the current action and controller, of the
            // ActionManager is set to properly update the DebugManager)
            this.opened(function() {
                setTimeout(function () {
                    var parent = self.getParent();
                    if (parent instanceof ActionManager) {
                        var action = parent.getCurrentActionInDialog();
                        if (action) {
                            var controller = parent.getCurrentControllerInDialog();
                            self.debugManager = new DebugManager(self);
                            var $header = self.$modal.find('.modal-header:first');
                            return self.debugManager.prependTo($header).then(function () {
                                self.debugManager.update('action', action, controller.widget);
                            });
                        }
                    }
                }, 0);
            });

            return this._super.apply(this, arguments);
        },
    });
}

return DebugManager;

});
