/* global vis, py */
odoo.define("web_timeline.TimelineRenderer", function (require) {
    "use strict";

    const AbstractRenderer = require("web.AbstractRenderer");
    const core = require("web.core");
    const time = require("web.time");
    const utils = require("web.utils");
    const session = require("web.session");
    const QWeb = require("web.QWeb");
    const field_utils = require("web.field_utils");
    const TimelineCanvas = require("web_timeline.TimelineCanvas");

    const _t = core._t;

    const TimelineRenderer = AbstractRenderer.extend({
        template: "TimelineView",

        events: _.extend({}, AbstractRenderer.prototype.events, {
            "click .oe_timeline_button_today": "_onTodayClicked",
            "click .oe_timeline_button_scale_day": "_onScaleDayClicked",
            "click .oe_timeline_button_scale_week": "_onScaleWeekClicked",
            "click .oe_timeline_button_scale_month": "_onScaleMonthClicked",
            "click .oe_timeline_button_scale_year": "_onScaleYearClicked",
        }),

        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.modelName = params.model;
            this.mode = params.mode;
            this.options = params.options;
            this.min_height = params.min_height;
            this.date_start = params.date_start;
            this.date_stop = params.date_stop;
            this.date_delay = params.date_delay;
            this.colors = params.colors;
            this.fieldNames = params.fieldNames;
            this.default_group_by = params.default_group_by;
            this.dependency_arrow = params.dependency_arrow;
            this.modelClass = params.view.model;
            this.fields = params.fields;

            this.timeline = false;
        },

        /**
         * @override
         */
        start: function () {
            const attrs = this.arch.attrs;
            this.current_window = {
                start: new moment(),
                end: new moment().add(24, "hours"),
            };

            this.$el.addClass(attrs.class);
            this.$timeline = this.$(".oe_timeline_widget");

            if (!this.date_start) {
                throw new Error(
                    _t("Timeline view has not defined 'date_start' attribute.")
                );
            }
            this._super.apply(this, arguments);
        },

        /**
         * Triggered when the timeline is attached to the DOM.
         */
        on_attach_callback: function () {
            const height =
                this.$el.parent().height() - this.$(".oe_timeline_buttons").height();
            if (height > this.min_height && this.timeline) {
                this.timeline.setOptions({
                    height: height,
                });
            }
        },

        /**
         * @override
         */
        _render: function () {
            return Promise.resolve().then(() => {
                // Prevent Double Rendering on Updates
                if (!this.timeline) {
                    this.init_timeline();
                    $(window).trigger("resize");
                }
            });
        },

        /**
         * Set the timeline window to today (day).
         *
         * @private
         */
        _onTodayClicked: function () {
            this.current_window = {
                start: new moment(),
                end: new moment().add(24, "hours"),
            };

            if (this.timeline) {
                this.timeline.setWindow(this.current_window);
            }
        },

        /**
         * Scale the timeline window to a day.
         *
         * @private
         */
        _onScaleDayClicked: function () {
            this._scaleCurrentWindow(24);
        },

        /**
         * Scale the timeline window to a week.
         *
         * @private
         */
        _onScaleWeekClicked: function () {
            this._scaleCurrentWindow(24 * 7);
        },

        /**
         * Scale the timeline window to a month.
         *
         * @private
         */
        _onScaleMonthClicked: function () {
            this._scaleCurrentWindow(
                24 * moment(this.current_window.start).daysInMonth()
            );
        },

        /**
         * Scale the timeline window to a year.
         *
         * @private
         */
        _onScaleYearClicked: function () {
            this._scaleCurrentWindow(
                24 * (moment(this.current_window.start).isLeapYear() ? 366 : 365)
            );
        },

        /**
         * Scales the timeline window based on the current window.
         *
         * @param {Integer} factor The timespan (in hours) the window must be scaled to.
         * @private
         */
        _scaleCurrentWindow: function (factor) {
            if (this.timeline) {
                this.current_window = this.timeline.getWindow();
                this.current_window.end = moment(this.current_window.start).add(
                    factor,
                    "hours"
                );
                this.timeline.setWindow(this.current_window);
            }
        },

        /**
         * Computes the initial visible window.
         *
         * @private
         */
        _computeMode: function () {
            if (this.mode) {
                let start = false,
                    end = false;
                switch (this.mode) {
                    case "day":
                        start = new moment().startOf("day");
                        end = new moment().endOf("day");
                        break;
                    case "week":
                        start = new moment().startOf("week");
                        end = new moment().endOf("week");
                        break;
                    case "month":
                        start = new moment().startOf("month");
                        end = new moment().endOf("month");
                        break;
                }
                if (end && start) {
                    this.options.start = start;
                    this.options.end = end;
                } else {
                    this.mode = "fit";
                }
            }
        },

        /**
         * Initializes the timeline
         * (https://visjs.github.io/vis-timeline/docs/timeline).
         *
         * @private
         */
        init_timeline: function () {
            this._computeMode();
            this.options.editable = {
                // Add new items by double tapping
                add: this.modelClass.data.rights.create,
                // Drag items horizontally
                updateTime: this.modelClass.data.rights.write,
                // Drag items from one group to another
                updateGroup: this.modelClass.data.rights.write,
                // Delete an item by tapping the delete button top right
                remove: this.modelClass.data.rights.unlink,
            };
            $.extend(this.options, {
                onAdd: this.on_add,
                onMove: this.on_move,
                onUpdate: this.on_update,
                onRemove: this.on_remove,
            });
            this.qweb = new QWeb(session.debug, {_s: session.origin}, false);
            if (this.arch.children.length) {
                const tmpl = utils.json_node_to_xml(
                    _.filter(this.arch.children, (item) => item.tag === "templates")[0]
                );
                this.qweb.add_template(tmpl);
            }

            this.timeline = new vis.Timeline(
                this.$timeline.get(0),
                {},
                {xss: {disabled: true}}
            );
            this.timeline.setOptions(this.options);
            if (this.mode && this["on_scale_" + this.mode + "_clicked"]) {
                this["on_scale_" + this.mode + "_clicked"]();
            }
            this.timeline.on("click", this.on_group_click);
            const group_bys = this.arch.attrs.default_group_by.split(",");
            this.last_group_bys = group_bys;
            this.last_domains = this.modelClass.data.domain;
            this.on_data_loaded(this.modelClass.data.data, group_bys);
            this.$centerContainer = $(this.timeline.dom.centerContainer);
            this.canvas = new TimelineCanvas(this);
            this.canvas.appendTo(this.$centerContainer);
            this.timeline.on("changed", () => {
                this.draw_canvas();
            });
        },

        /**
         * Clears and draws the canvas items.
         *
         * @private
         */
        draw_canvas: function () {
            this.canvas.clear();
            if (this.dependency_arrow) {
                this.draw_dependencies();
            }
        },

        /**
         * Draw item dependencies on canvas.
         *
         * @private
         */
        draw_dependencies: function () {
            const items = this.timeline.itemSet.items;
            const datas = this.timeline.itemsData;
            if (!items || !datas) {
                return;
            }
            const keys = Object.keys(items);
            for (const key of keys) {
                const item = items[key];
                const data = datas.get(Number(key));
                if (!data || !data.evt) {
                    return;
                }
                for (const id of data.evt[this.dependency_arrow]) {
                    if (keys.indexOf(id.toString()) !== -1) {
                        this.draw_dependency(item, items[id]);
                    }
                }
            }
        },

        /**
         * Draws a dependency arrow between 2 timeline items.
         *
         * @param {Object} from Start timeline item
         * @param {Object} to Destination timeline item
         * @param {Object} options
         * @param {Object} options.line_color Color of the line
         * @param {Object} options.line_width The width of the line
         * @private
         */
        draw_dependency: function (from, to, options) {
            if (!from.displayed || !to.displayed) {
                return;
            }
            const defaults = _.defaults({}, options, {
                line_color: "black",
                line_width: 1,
            });
            this.canvas.draw_arrow(
                from.dom.box,
                to.dom.box,
                defaults.line_color,
                defaults.line_width
            );
        },

        /**
         * Load display_name of records.
         *
         * @param {Object[]} events
         * @param {String[]} group_bys
         * @param {Boolean} adjust_window
         * @private
         * @returns {jQuery.Deferred}
         */
        on_data_loaded: function (events, group_bys, adjust_window) {
            const ids = _.pluck(events, "id");
            return this._rpc({
                model: this.modelName,
                method: "name_get",
                args: [ids],
                context: this.getSession().user_context,
            }).then((names) => {
                const nevents = _.map(events, (event) =>
                    _.extend(
                        {
                            __name: _.detect(names, (name) => name[0] === event.id)[1],
                        },
                        event
                    )
                );
                return this.on_data_loaded_2(nevents, group_bys, adjust_window);
            });
        },

        /**
         * Set groups and events.
         *
         * @param {Object[]} events
         * @param {String[]} group_bys
         * @param {Boolean} adjust_window
         * @private
         */
        on_data_loaded_2: function (events, group_bys, adjust_window) {
            const data = [];
            this.grouped_by = group_bys;
            for (const evt of events) {
                if (evt[this.date_start]) {
                    data.push(this.event_data_transform(evt));
                }
            }
            this.split_groups(events, group_bys).then((groups) => {
                this.timeline.setGroups(groups);
                this.timeline.setItems(data);
                const mode = !this.mode || this.mode === "fit";
                const adjust = _.isUndefined(adjust_window) || adjust_window;
                if (mode && adjust) {
                    this.timeline.fit();
                }
            });
        },

        /**
         * Get the groups.
         *
         * @param {Object[]} events
         * @param {String[]} group_bys
         * @private
         * @returns {Array}
         */
        split_groups: async function (events, group_bys) {
            if (group_bys.length === 0) {
                return events;
            }
            const groups = [];
            groups.push({id: -1, content: _t("<b>UNASSIGNED</b>"), order: -1});
            var seq = 1;
            for (const evt of events) {
                const grouped_field = _.first(group_bys);
                const group_name = evt[grouped_field];
                if (group_name) {
                    if (group_name instanceof Array) {
                        const group = _.find(
                            groups,
                            (existing_group) => existing_group.id === group_name[0]
                        );
                        if (_.isUndefined(group)) {
                            // Check if group is m2m in this case add id -> value of all
                            // found entries.
                            await this._rpc({
                                model: this.modelName,
                                method: "fields_get",
                                args: [grouped_field],
                                context: this.getSession().user_context,
                            }).then(async (fields) => {
                                if (fields[grouped_field].type === "many2many") {
                                    const list_values =
                                        await this.get_m2m_grouping_datas(
                                            fields[grouped_field].relation,
                                            group_name
                                        );
                                    for (const vals of list_values) {
                                        let is_inside = false;
                                        for (const gr of groups) {
                                            if (vals.id === gr.id) {
                                                is_inside = true;
                                                break;
                                            }
                                        }
                                        if (!is_inside) {
                                            vals.order = seq;
                                            seq += 1;
                                            groups.push(vals);
                                        }
                                    }
                                } else {
                                    groups.push({
                                        id: group_name[0],
                                        content: group_name[1],
                                        order: seq,
                                    });
                                    seq += 1;
                                }
                            });
                        }
                    }
                }
            }
            return groups;
        },

        get_m2m_grouping_datas: async function (model, group_name) {
            const groups = [];
            for (const gr of group_name) {
                await this._rpc({
                    model: model,
                    method: "name_get",
                    args: [gr],
                    context: this.getSession().user_context,
                }).then((name) => {
                    groups.push({id: name[0][0], content: name[0][1]});
                });
            }
            return groups;
        },

        /**
         * Get dates from given event
         *
         * @param {TransformEvent} evt
         * @returns {Object}
         */
        _get_event_dates: function (evt) {
            let date_start = new moment();
            let date_stop = null;

            const date_delay = evt[this.date_delay] || false,
                all_day = this.all_day ? evt[this.all_day] : false;

            if (all_day) {
                date_start = time.auto_str_to_date(
                    evt[this.date_start].split(" ")[0],
                    "start"
                );
                if (this.no_period) {
                    date_stop = date_start;
                } else {
                    date_stop = this.date_stop
                        ? time.auto_str_to_date(
                              evt[this.date_stop].split(" ")[0],
                              "stop"
                          )
                        : null;
                }
            } else {
                date_start = time.auto_str_to_date(evt[this.date_start]);
                date_stop = this.date_stop
                    ? time.auto_str_to_date(evt[this.date_stop])
                    : null;
            }

            if (!date_stop && date_delay) {
                date_stop = date_start.clone().add(date_delay, "hours").toDate();
            }

            return [date_start, date_stop];
        },

        /**
         * Transform Odoo event object to timeline event object.
         *
         * @param {TransformEvent} evt
         * @private
         * @returns {Object}
         */
        event_data_transform: function (evt) {
            const [date_start, date_stop] = this._get_event_dates(evt);
            let group = evt[this.last_group_bys[0]];
            if (group && group instanceof Array && group.length > 0) {
                group = _.first(group);
            } else {
                group = -1;
            }

            for (const color of this.colors) {
                if (py.eval(`'${evt[color.field]}' ${color.opt} '${color.value}'`)) {
                    this.color = color.color;
                }
            }

            let content = evt.__name || evt.display_name;
            if (this.arch.children.length) {
                content = this.render_timeline_item(evt);
            }

            const r = {
                start: date_start,
                content: content,
                id: evt.id,
                order: evt.order,
                group: group,
                evt: evt,
                style: `background-color: ${this.color};`,
            };
            // Check if the event is instantaneous,
            // if so, display it with a point on the timeline (no 'end')
            if (date_stop && !moment(date_start).isSame(date_stop)) {
                r.end = date_stop;
            }
            this.color = null;
            return r;
        },

        /**
         * Render timeline item template.
         *
         * @param {Object} evt Record
         * @private
         * @returns {String} Rendered template
         */
        render_timeline_item: function (evt) {
            if (this.qweb.has_template("timeline-item")) {
                return this.qweb.render("timeline-item", {
                    record: evt,
                    field_utils: field_utils,
                });
            }

            console.error(
                _t('Template "timeline-item" not present in timeline view definition.')
            );
        },

        /**
         * Handle a click on a group header.
         *
         * @param {ClickEvent} e
         * @private
         */
        on_group_click: function (e) {
            if (e.what === "group-label" && e.group !== -1) {
                this._trigger(
                    e,
                    () => {
                        // Do nothing
                    },
                    "onGroupClick"
                );
            }
        },

        /**
         * Trigger onUpdate.
         *
         * @param {Object} item
         * @param {Function} callback
         * @private
         */
        on_update: function (item, callback) {
            this._trigger(item, callback, "onUpdate");
        },

        /**
         * Trigger onMove.
         *
         * @param {Object} item
         * @param {Function} callback
         * @private
         */
        on_move: function (item, callback) {
            this._trigger(item, callback, "onMove");
        },

        /**
         * Trigger onRemove.
         *
         * @param {Object} item
         * @param {Function} callback
         * @private
         */
        on_remove: function (item, callback) {
            this._trigger(item, callback, "onRemove");
        },

        /**
         * Trigger onAdd.
         *
         * @param {Object} item
         * @param {Function} callback
         * @private
         */
        on_add: function (item, callback) {
            this._trigger(item, callback, "onAdd");
        },

        /**
         * Trigger_up encapsulation adds by default the rights, and the renderer.
         *
         * @param {HTMLElement} item
         * @param {Function} callback
         * @param {String} trigger
         * @private
         */
        _trigger: function (item, callback, trigger) {
            this.trigger_up(trigger, {
                item: item,
                callback: callback,
                rights: this.modelClass.data.rights,
                renderer: this,
            });
        },
    });

    return TimelineRenderer;
});
