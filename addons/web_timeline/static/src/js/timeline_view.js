/* global py */
/* Odoo web_timeline
 * Copyright 2015 ACSONE SA/NV
 * Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
 * Copyright 2023 Onestein - Anjeel Haria
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

odoo.define("web_timeline.TimelineView", function (require) {
    "use strict";

    const core = require("web.core");
    const utils = require("web.utils");
    const view_registry = require("web.view_registry");
    const AbstractView = require("web.AbstractView");
    const TimelineRenderer = require("web_timeline.TimelineRenderer");
    const TimelineController = require("web_timeline.TimelineController");
    const TimelineModel = require("web_timeline.TimelineModel");

    const _lt = core._lt;

    function isNullOrUndef(value) {
        return _.isUndefined(value) || _.isNull(value);
    }

    var TimelineView = AbstractView.extend({
        display_name: _lt("Timeline"),
        icon: "fa fa-tasks",
        jsLibs: ["/web_timeline/static/lib/vis-timeline/vis-timeline-graph2d.js"],
        cssLibs: ["/web_timeline/static/lib/vis-timeline/vis-timeline-graph2d.css"],
        config: _.extend({}, AbstractView.prototype.config, {
            Model: TimelineModel,
            Controller: TimelineController,
            Renderer: TimelineRenderer,
        }),
        viewType: "timeline",

        /**
         * @override
         */
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);
            this.modelName = this.controllerParams.modelName;

            const action = params.action;
            this.arch = this.rendererParams.arch;
            const attrs = this.arch.attrs;
            const date_start = attrs.date_start;
            const date_stop = attrs.date_stop;
            const date_delay = attrs.date_delay;
            const dependency_arrow = attrs.dependency_arrow;

            const fields = viewInfo.fields;
            let fieldNames = fields.display_name ? ["display_name"] : [];
            const fieldsToGather = [
                "date_start",
                "date_stop",
                "default_group_by",
                "progress",
                "date_delay",
                attrs.default_group_by,
            ];

            for (const field of fieldsToGather) {
                if (attrs[field]) {
                    fieldNames.push(attrs[field]);
                }
            }

            const archFieldNames = _.map(
                _.filter(this.arch.children, (item) => item.tag === "field"),
                (item) => item.attrs.name
            );
            fieldNames = _.union(fieldNames, archFieldNames);

            const colors = this.parse_colors();
            for (const color of colors) {
                if (!fieldNames.includes(color.field)) {
                    fieldNames.push(color.field);
                }
            }

            if (dependency_arrow) {
                fieldNames.push(dependency_arrow);
            }

            const mode = attrs.mode || attrs.default_window || "fit";
            const min_height = attrs.min_height || 300;

            const current_window = {
                start: new moment(),
                end: new moment().add(24, "hours"),
            };
            if (!isNullOrUndef(attrs.quick_create_instance)) {
                this.quick_create_instance = "instance." + attrs.quick_create_instance;
            }
            let open_popup_action = false;
            if (
                !isNullOrUndef(attrs.event_open_popup) &&
                utils.toBoolElse(attrs.event_open_popup, true)
            ) {
                open_popup_action = attrs.event_open_popup;
            }
            this.rendererParams.mode = mode;
            this.rendererParams.model = this.modelName;
            this.rendererParams.view = this;
            this.rendererParams.options = this._preapre_vis_timeline_options(attrs);
            this.rendererParams.current_window = current_window;
            this.rendererParams.date_start = date_start;
            this.rendererParams.date_stop = date_stop;
            this.rendererParams.date_delay = date_delay;
            this.rendererParams.colors = colors;
            this.rendererParams.fieldNames = fieldNames;
            this.rendererParams.default_group_by = attrs.default_group_by;
            this.rendererParams.min_height = min_height;
            this.rendererParams.dependency_arrow = dependency_arrow;
            this.rendererParams.fields = fields;
            this.loadParams.modelName = this.modelName;
            this.loadParams.fieldNames = fieldNames;
            this.loadParams.default_group_by = attrs.default_group_by;
            this.controllerParams.open_popup_action = open_popup_action;
            this.controllerParams.date_start = date_start;
            this.controllerParams.date_stop = date_stop;
            this.controllerParams.date_delay = date_delay;
            this.controllerParams.actionContext = action.context;
            this.withSearchPanel = false;
        },

        _preapre_vis_timeline_options: function (attrs) {
            return {
                groupOrder: "order",
                orientation: "both",
                selectable: true,
                multiselect: true,
                showCurrentTime: true,
                stack: isNullOrUndef(attrs.stack)
                    ? true
                    : utils.toBoolElse(attrs.stack, true),
                margin: attrs.margin ? JSON.parse(attrs.margin) : {item: 2},
                zoomKey: attrs.zoomKey || "ctrlKey",
            };
        },

        /**
         * Parse the colors attribute.
         *
         * @private
         * @returns {Array}
         */
        parse_colors: function () {
            if (this.arch.attrs.colors) {
                return _(this.arch.attrs.colors.split(";"))
                    .chain()
                    .compact()
                    .map((color_pair) => {
                        const pair = color_pair.split(":");
                        const color = pair[0];
                        const expr = pair[1];
                        const temp = py.parse(py.tokenize(expr));
                        return {
                            color: color,
                            field: temp.expressions[0].value,
                            opt: temp.operators[0],
                            value: temp.expressions[1].value,
                        };
                    })
                    .value();
            }
            return [];
        },
    });

    view_registry.add("timeline", TimelineView);
    return TimelineView;
});
