/** @odoo-module **/
"use strict";

import { ComponentAdapter } from "web.OwlCompatibility";
import { FieldMany2ManyTags } from "web.relational_fields";
import StandaloneFieldManagerMixin from "web.StandaloneFieldManagerMixin";
import Widget from "web.Widget";

const { Component, xml } = owl;

/**
 * This widget is used in the global filters to select a value for a
 * relation filter
 * It uses a FieldMany2ManyTags widget.
 */
const TagSelectorWidget = Widget.extend(StandaloneFieldManagerMixin, {
    /**
     * @constructor
     *
     * @param {string} relatedModel Name of the related model
     * @param {Array<number>} selectedValues Values already selected
     * @param {string | undefined} placeholder
     */
    init: function (parent, relatedModel, selectedValues, placeholder) {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.relatedModel = relatedModel;
        this.selectedValues = selectedValues;
        this.placeholder = placeholder;
        this.widget = undefined;
    },
    updateWidgetState: async function (state) {
        this.selectedValues = state.selectedValues;
        this.relatedModel = state.relatedModel;
        await this._makeM2MWidget();
        const $content = $("<div/>");
        this.$el.empty().append($content);
        this.widget.appendTo($content);
    },
    /**
     * @override
     */
    willStart: async function () {
        await this._super.apply(this, arguments);
        await this._makeM2MWidget();
    },
    /**
     * @override
     */
    start: function () {
        const $content = $("<div/>");
        this.$el.append($content);
        this.widget.appendTo($content);
        return this._super.apply(this, arguments);
    },
    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _confirmChange: async function () {
        const result = await StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
        this.trigger_up("value_changed", {
            value: this.widget.value.data.map((record) => record.data),
        });
        return result;
    },
    /**
     * Create a record for the related model and a FieldMany2ManyTags linked
     * to this record
     */
    _makeM2MWidget: async function () {
        const options = {};
        options[this.relatedModel] = {
            options: {
                no_create_edit: true,
                no_create: true,
            },
        };
        const recordID = await this.model.makeRecord(
            this.relatedModel,
            [
                {
                    fields: [
                        {
                            name: "id",
                            type: "integer",
                        },
                        {
                            name: "display_name",
                            type: "char",
                        },
                    ],
                    name: this.relatedModel,
                    relation: this.relatedModel,
                    type: "many2many",
                    value: this.selectedValues,
                },
            ],
            options
        );
        this.widget = new FieldMany2ManyTags(this, this.relatedModel, this.model.get(recordID), {
            mode: "edit",
            attrs: { placeholder: this.placeholder },
        });
        this._registerWidget(recordID, this.relatedModel, this.widget);
    },
});

class TagSelectorWidgetAdapter extends ComponentAdapter {
    setup() {
        super.setup();
        this.env = Component.env;
    }

    _trigger_up(ev) {
        if (ev.name === "value_changed") {
            const { value } = ev.data;
            return this.props.onValueChanged(value);
        }
        super._trigger_up(ev);
    }

    /**
     * @override
     */
    get widgetArgs() {
        return [this.props.relatedModel, this.props.selectedValues, this.props.placeholder];
    }

    /**
     * @override
     */
    async updateWidget(nextProps) {
        if (
            nextProps.relatedModel !== this.props.relatedModel ||
            JSON.stringify(nextProps.selectedValues) !== JSON.stringify(this.props.selectedValues)
        ) {
            const payload = {
                relatedModel: nextProps.relatedModel,
                selectedValues: nextProps.selectedValues,
            };
            return this.widget.updateWidgetState(payload);
        }
    }

    /**
     * @override
     */
    renderWidget() {}
}

export class X2ManyTagSelector extends Component {
    setup() {
        this.TagSelectorWidget = TagSelectorWidget;
    }
}
X2ManyTagSelector.components = { TagSelectorWidgetAdapter };
X2ManyTagSelector.template = xml/*xml*/ `
    <TagSelectorWidgetAdapter
        Component="TagSelectorWidget"
        relatedModel="props.relatedModel"
        selectedValues="props.selectedValues"
        onValueChanged="props.onValueChanged"
        placeholder="props.placeholder"
    />`;
X2ManyTagSelector.props = {
    onValueChanged: Function,
    relatedModel: String,
    selectedValues: {
        optional: true,
        type: Array,
    },
    placeholder: {
        optional: true,
        type: String,
    },
};
X2ManyTagSelector.defaultProps = {
    selectedValues: [],
};
