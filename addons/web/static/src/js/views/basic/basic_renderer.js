odoo.define('web.BasicRenderer', function (require) {
"use strict";

/**
 * The BasicRenderer is an abstract class designed to share code between all
 * views that uses a BasicModel.  The main goal is to keep track of all field
 * widgets, and properly destroy them whenever a rerender is done.
 *
 * When a concrete view extends a BasicRenderer, it should add each field
 * widgets in the this.widget list.
 */

var AbstractRenderer = require('web.AbstractRenderer');
var config = require('web.config');
var core = require('web.core');

var qweb = core.qweb;

return AbstractRenderer.extend({
    /**
     * @override
     */
    init: function (paret, state, params) {
        this._super.apply(this, arguments);
        this.widgets = [];
        this.activeActions = params.activeActions;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a tooltip on a $node, depending on a field description
     *
     * @param {FieldWidget} widget
     * @param {$node} $node
     */
    _addFieldTooltip: function (widget, $node) {
        // optional argument $node, the jQuery element on which the tooltip
        // should be attached if not given, the tooltip is attached on the
        // widget's $el
        $node = $node.length ? $node : widget.$el;
        $node.tooltip({
            delay: { show: 1000, hide: 0 },
            title: function () {
                return qweb.render('WidgetLabel.tooltip', {
                    debug: config.debug,
                    widget: widget,
                });
            }
        });
    },
    /**
     * Helper method, used to get an object with the 'raw' field values. It is
     * important when we want to evaluate if a record matches a given domain.
     *
     * A basic model record is a tree structure, but we sometimes need 'pure'
     * data, so for example, [1,4] for the value of a one2many, not
     * [{Object}, {Object}].
     *
     * @param {Object} record
     * @returns {Object}
     */
    _getFieldValues: function (record) {
        var result = {};
        _.each(record.fieldNames, function (name) {
            var field = record.fields[name];
            var value = record.data[name];
            result[name] = value;
            if (!value) {
                return;
            }
            else if (field.type === 'many2one') {
                result[name] = value.data ? value.data.id || false : false;
            }
            else if (field.type === 'one2many' || field.type === 'many2many') {
                if (value) {
                    result[name] = _.pluck(value.data, 'res_id');
                } else {
                    result[name] = [];
                }
            }
            else if (field.type === 'boolean') {
                // we want an explicit false value, not null if it is unset
                result[name] = value || false;
            }
        });
        result.id = record.data.id;
        return result;
    },
    /**
     * Render the view
     *
     * @override
     * @returns {Deferred}
     */
    _render: function () {
        var oldWidgets = this.widgets;
        this.widgets = [];
        return this._renderView().then(_.invoke.bind(_, oldWidgets, 'destroy'));
    },
    /**
     * Actual rendering. Supposed to be overridden by concrete renderers.
     * The basic responsabilities of _renderView are:
     * - use the xml arch of the view to render a jQuery representation
     * - instantiate a widget from the registry for each field in the arch
     *
     * Note that the 'state' field should contains all necessary information
     * for the rendering.  The field widgets should be as synchronous as
     * possible.
     *
     * @abstract
     * @returns {Deferred}
     */
    _renderView: function () {
        return $.when();
    },
});

});
