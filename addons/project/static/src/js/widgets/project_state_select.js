/** @odoo-module **/

import {qweb} from 'web.core';
import fieldRegistry from 'web.field_registry';
import {StateSelectionWidget} from 'web.basic_fields';


/**
 * List of colors according to the selection value, see `project_update.py`
 */
const STATUS_COLORS = {
    'on_track': 10,
    'at_risk': 2,
    'off_track': 1,
    'on_hold': 4,
};

export const ProjectStateSelectionWidget = StateSelectionWidget.extend({

    /**
     * @override
     */
    init() {
        this._super.apply(this, arguments);
        // The dropdown never disappears without `edit` mode on.
        this.mode = 'edit';
    },

    /**
     * @override
     * @private
     */
    _prepareDropdownValues() {
        const self = this;
        const _data = [];
        const current_state_id = self.recordData.last_update_status;
        _.map(this.field.selection || [], function(selection_item) {
            // Exclude `to_define` from the dropdown list
            if (selection_item[0] === 'to_define' && current_state_id !== 'to_define') {
                return;
            }
            const value = {
                'name': selection_item[0],
                'tooltip': selection_item[1],
            };
            value.state_class = 'o_status_bubble mx-0 o_color_bubble_' + STATUS_COLORS[selection_item[0]];
            value.state_name = selection_item[1];
            _data.push(value);
        });
        return _data;
    },

    /**
     * @override
     * @private
     */
    _render() {
        // Complete override since most of `StateSelectionWidget` is hardcoded.
        // See `_render` from `StateSelectionWidget`
        const states = this._prepareDropdownValues();
        const currentState = _.findWhere(states, {name: this.value}) || states[0];
        this.$('.o_status')
            .removeClass('o_status_bubble mx-0 o_color_bubble_10 o_color_bubble_2 o_color_bubble_1 o_color_bubble_4')
            .addClass(currentState.state_class)
            .prop('special_click', true)
            .parent().attr('title', currentState.state_name)
            .attr('aria-label', this.string + ": " + currentState.state_name);

        const $items = $(qweb.render('FormSelection.items', {
            states: _.without(states, currentState)
        }));
        const $dropdown = this.$('.dropdown-menu');
        $dropdown.children().remove();
        $items.appendTo($dropdown);

        const isReadonly = this.record.evalModifiers(this.attrs.modifiers).readonly;
        this.$('a[data-bs-toggle=dropdown]').toggleClass('disabled', isReadonly || false);
    }
});

fieldRegistry.add('project_state_selection', ProjectStateSelectionWidget);
