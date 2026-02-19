/** @odoo-module **/

import BasicModel from "web.BasicModel";
import {ComponentAdapter} from "web.OwlCompatibility";
import {Dropdown} from "@web/core/dropdown/dropdown";
import FieldManagerMixin from "web.FieldManagerMixin";
import {FieldMany2One} from "web.relational_fields";
import {SelectCreateDialog} from "web.view_dialogs";
import {patch} from "@web/core/utils/patch";
import {session} from "@web/session";

const {Component, xml} = owl;

patch(Dropdown.prototype, "dropdown", {
    onWindowClicked(ev) {
        // This patch is created to prevent the closing of the Filter menu
        // when a selection is made in the RecordPicker
        if ($(ev.target.closest("ul.dropdown-menu")).attr("id") !== undefined) {
            const dropdown = $("body > ul.dropdown-menu");
            for (let i = 0; i < dropdown.length; i++) {
                if (
                    $(ev.target.closest("ul.dropdown-menu")).attr("id") ===
                    $(dropdown[i]).attr("id")
                ) {
                    return;
                }
            }
        }
        this._super(ev);
    },
});

export const FakeMany2oneFieldWidget = FieldMany2One.extend(FieldManagerMixin, {
    supportedFieldTypes: ["many2many", "many2one", "one2many"],
    /**
     * @override
     */
    init: function (parent) {
        this.componentAdapter = parent;
        const options = this.componentAdapter.props.attrs;
        // Create a dummy record with only a dummy m2o field to search on
        const model = new BasicModel("dummy");
        const params = {
            fieldNames: ["dummy"],
            modelName: "dummy",
            context: {},
            type: "record",
            viewType: "default",
            fieldsInfo: {default: {dummy: {}}},
            fields: {
                dummy: {
                    string: options.string,
                    relation: options.model,
                    context: options.context,
                    domain: options.domain,
                    type: "many2one",
                },
            },
        };
        // Emulate `model.load()`, without RPC-calling `default_get()`
        this.dataPointID = model._makeDataPoint(params).id;
        model.generateDefaultValues(this.dataPointID, {});
        this._super(this.componentAdapter, "dummy", this._get_record(model), {
            mode: "edit",
            attrs: {
                options: {
                    no_create_edit: true,
                    no_create: true,
                    no_open: true,
                    no_quick_create: true,
                },
            },
        });
        FieldManagerMixin.init.call(this, model);
    },
    /**
     * Get record
     *
     * @param {BasicModel} model
     * @returns {String}
     */
    _get_record: function (model) {
        return model.get(this.dataPointID);
    },
    /**
     * @override
     */
    _confirmChange: function (id, fields, event) {
        this.componentAdapter.trigger("change", event.data.changes[fields[0]]);
        this.dataPointID = id;
        return this.reset(this._get_record(this.model), event);
    },
    /**
     * Stop propagation of the 'Search more..' dialog click event.
     * Otherwise, the filter's dropdown will be closed after a selection.
     *
     * @override
     */
    _searchCreatePopup: function (view, ids, context, dynamicFilters) {
        const options = this._getSearchCreatePopupOptions(
            view,
            ids,
            context,
            dynamicFilters
        );
        const dialog = new SelectCreateDialog(
            this,
            _.extend({}, this.nodeOptions, options)
        );
        // Hack to stop click event propagation
        dialog._opened.then(() =>
            dialog.$el
                .get(0)
                .addEventListener("click", (event) => event.stopPropagation())
        );
        return dialog.open();
    },
    _onFieldChanged: function (event) {
        const self = this;
        event.stopPropagation();
        if (event.data.changes.dummy.display_name === undefined) {
            return this._rpc({
                model: this.field.relation,
                method: "name_get",
                args: [event.data.changes.dummy.id],
                context: session.user_context,
            }).then(function (result) {
                event.data.changes.dummy.display_name = result[0][1];
                return (
                    self
                        ._applyChanges(
                            event.data.dataPointID,
                            event.data.changes,
                            event
                        )
                        // eslint-disable-next-line no-empty-function
                        .then(event.data.onSuccess || function () {})
                        // eslint-disable-next-line no-empty-function
                        .guardedCatch(event.data.onFailure || function () {})
                );
            });
        }
        return (
            this._applyChanges(event.data.dataPointID, event.data.changes, event)
                // eslint-disable-next-line no-empty-function
                .then(event.data.onSuccess || function () {})
                // eslint-disable-next-line no-empty-function
                .guardedCatch(event.data.onFailure || function () {})
        );
    },
});

export class FakeMany2oneFieldWidgetAdapter extends ComponentAdapter {
    constructor() {
        super(...arguments);
        this.env = Component.env;
    }

    renderWidget() {
        this.widget._render();
    }

    get widgetArgs() {
        if (this.props.widgetArgs) {
            return this.props.widgetArgs;
        }
        return [this.props.attrs];
    }
}

/**
 * A record selector widget.
 *
 * Underneath, it implements and extends the `FieldManagerMixin`, and acts as if it
 * were a reduced dummy controller. Some actions "mock" the underlying model, since
 * sometimes we use a char widget to fill related fields (which is not supported by
 * that widget), and fields need an underlying model implementation, which can only
 * hold fake data, given a search view has no data on it by definition.
 *
 * @extends Component
 */
export class RecordPicker extends Component {
    setup() {
        this.attrs = {
            string: this.props.string,
            model: this.props.model,
            domain: this.props.domain,
            context: this.props.context,
        };
        this.FakeMany2oneFieldWidget = FakeMany2oneFieldWidget;
    }
}

RecordPicker.template = xml`
    <div>
        <FakeMany2oneFieldWidgetAdapter
            Component="FakeMany2oneFieldWidget"
            class="d-block"
            attrs="attrs"
        />
    </div>`;
RecordPicker.components = {FakeMany2oneFieldWidgetAdapter};
