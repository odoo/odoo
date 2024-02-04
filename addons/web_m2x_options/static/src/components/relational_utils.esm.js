/** @odoo-module **/

import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {patch} from "@web/core/utils/patch";
import {sprintf} from "@web/core/utils/strings";
const {Component} = owl;

export function is_option_set(option) {
    if (_.isUndefined(option)) return false;
    if (typeof option === "string") return option === "true" || option === "True";
    if (typeof option === "boolean") return option;
    return false;
}

patch(Many2XAutocomplete.prototype, "web_m2x_options.Many2XAutocomplete", {
    setup() {
        this._super(...arguments);
        this.ir_options = Component.env.session.web_m2x_options;
    },

    async loadOptionsSource(request) {
        if (this.lastProm) {
            this.lastProm.abort(false);
        }
        // Add options limit used to change number of selections record
        // returned.
        if (!_.isUndefined(this.ir_options["web_m2x_options.limit"])) {
            this.props.searchLimit = parseInt(
                this.ir_options["web_m2x_options.limit"],
                10
            );
            this.limit = this.props.searchLimit;
        }

        if (typeof this.props.nodeOptions.limit === "number") {
            this.props.searchLimit = this.props.nodeOptions.limit;
            this.limit = this.props.searchLimit;
        }

        // Add options field_color and colors to color item(s) depending on field_color value
        this.field_color = this.props.nodeOptions.field_color;
        this.colors = this.props.nodeOptions.colors;

        this.lastProm = this.orm.call(this.props.resModel, "name_search", [], {
            name: request,
            operator: "ilike",
            args: this.props.getDomain(),
            limit: this.props.searchLimit + 1,
            context: this.props.context,
        });
        const records = await this.lastProm;

        var options = records.map((result) => ({
            value: result[0],
            id: result[0],
            label: result[1].split("\n")[0],
        }));

        // Limit results if there is a custom limit options
        if (this.limit) {
            options = options.slice(0, this.props.searchLimit);
        }

        // Search result value colors
        if (this.colors && this.field_color) {
            var value_ids = options.map((result) => result.value);
            const objects = await this.orm.call(
                this.props.resModel,
                "search_read",
                [],
                {
                    domain: [["id", "in", value_ids]],
                    fields: [this.field_color],
                }
            );
            for (var index in objects) {
                for (var index_value in options) {
                    if (options[index_value].id === objects[index].id) {
                        // Find value in values by comparing ids
                        var option = options[index_value];
                        // Find color with field value as key
                        var color =
                            this.colors[objects[index][this.field_color]] || "black";
                        option.style = "color:" + color;
                        break;
                    }
                }
            }
        }

        // Quick create
        // Note: Create should be before `search_more` (reserve native order)
        // One more reason: when calling `onInputBlur`, native select the first option (activeSourceOption)
        // which triggers m2o_dialog if m2o_dialog=true
        var create_enabled =
            this.props.quickCreate && !this.props.nodeOptions.no_create;

        var raw_result = _.map(records, function (x) {
            return x[1];
        });
        var quick_create = is_option_set(this.props.nodeOptions.create),
            quick_create_undef = _.isUndefined(this.props.nodeOptions.create),
            m2x_create_undef = _.isUndefined(this.ir_options["web_m2x_options.create"]),
            m2x_create = is_option_set(this.ir_options["web_m2x_options.create"]);
        var show_create =
            (!this.props.nodeOptions && (m2x_create_undef || m2x_create)) ||
            (this.props.nodeOptions &&
                (quick_create ||
                    (quick_create_undef && (m2x_create_undef || m2x_create))));
        if (
            create_enabled &&
            !this.props.nodeOptions.no_quick_create &&
            request.length > 0 &&
            !_.contains(raw_result, request) &&
            show_create
        ) {
            options.push({
                label: sprintf(this.env._t(`Create "%s"`), request),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create",
                action: async (params) => {
                    try {
                        await this.props.quickCreate(request, params);
                    } catch {
                        const context = this.getCreationContext(request);
                        return this.openMany2X({context});
                    }
                },
            });
        }

        // Search more...
        // Resolution order:
        // 1- check if "search_more" is set locally in node's options
        // 2- if set locally, apply its value
        // 3- if not set locally, check if it's set globally via ir.config_parameter
        // 4- if set globally, apply its value
        // 5- if not set globally either, check if returned values are more than node's limit
        var search_more = false;
        if (!_.isUndefined(this.props.nodeOptions.search_more)) {
            search_more = is_option_set(this.props.nodeOptions.search_more);
        } else if (!_.isUndefined(this.ir_options["web_m2x_options.search_more"])) {
            search_more = is_option_set(this.ir_options["web_m2x_options.search_more"]);
        } else {
            search_more =
                !this.props.noSearchMore && this.props.searchLimit < records.length;
        }
        if (search_more) {
            options.push({
                label: this.env._t("Search More..."),
                action: this.onSearchMore.bind(this, request),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
            });
        }

        // Create and Edit
        const canCreateEdit =
            "createEdit" in this.activeActions
                ? this.activeActions.createEdit
                : this.activeActions.create;
        if (
            !request.length &&
            !this.props.value &&
            (this.props.quickCreate || canCreateEdit)
        ) {
            options.push({
                label: this.env._t("Start typing..."),
                classList: "o_m2o_start_typing",
                unselectable: true,
            });
        }

        // Create and edit ...
        var create_edit =
                is_option_set(this.props.nodeOptions.create) ||
                is_option_set(this.props.nodeOptions.create_edit),
            create_edit_undef =
                _.isUndefined(this.props.nodeOptions.create) &&
                _.isUndefined(this.props.nodeOptions.create_edit),
            m2x_create_edit_undef = _.isUndefined(
                this.ir_options["web_m2x_options.create_edit"]
            ),
            m2x_create_edit = is_option_set(
                this.ir_options["web_m2x_options.create_edit"]
            );
        var show_create_edit =
            (!this.props.nodeOptions && (m2x_create_edit_undef || m2x_create_edit)) ||
            (this.props.nodeOptions &&
                (create_edit ||
                    (create_edit_undef && (m2x_create_edit_undef || m2x_create_edit))));
        if (
            create_enabled &&
            !this.props.nodeOptions.no_create_edit &&
            show_create_edit &&
            request.length &&
            canCreateEdit
        ) {
            const context = this.getCreationContext(request);
            options.push({
                label: this.env._t("Create and edit..."),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create_edit",
                action: () => this.openMany2X({context}),
            });
        }

        // No records
        if (!records.length && !this.activeActions.create) {
            options.push({
                label: this.env._t("No records"),
                classList: "o_m2o_no_result",
                unselectable: true,
            });
        }

        return options;
    },
});

Many2XAutocomplete.defaultProps = {
    ...Many2XAutocomplete.defaultProps,
    nodeOptions: {},
};
