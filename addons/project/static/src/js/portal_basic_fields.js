odoo.define('project.portalBasicFields', function (require) {
    "use strict";
    
    var basic_fields = require('web.basic_fields');
    var registry = require('web.field_registry')

    var PriorityWidget = basic_fields.PriorityWidget;
    var StateSelectionWidget = basic_fields.StateSelectionWidget;
    
    /**
     * Disable all interaction with PriorityWidget
     */
    var ReadOnlyPriorityWidget = PriorityWidget.extend({
        events: {},
        _renderStar: function (tag, isFull, index, tip) {
            return this._super.apply(this, arguments)
                .removeAttr('href');
        }
    });

    /**
     * Disable all interaction with StateSelectionWidget
     */
    var ReadOnlyStateSelectionWidget = StateSelectionWidget.extend({
        events: {},
        _render: function () {
            var self = this;
            var states = this._prepareDropdownValues();
            // Adapt "FormSelection"
            // Like priority, default on the first possible value if no value is given.
            var currentState = _.findWhere(states, {name: self.value}) || states[0];
            this.$('.o_status')
                .removeClass('o_status_red o_status_green')
                .addClass(currentState.state_class)
                .parent().attr('title', currentState.state_name)
                .attr('aria-label', currentState.state_name)
                .removeAttr('href')
                .removeAttr('data-toggle')
                .removeData('toggle');
        },
    });

    registry.add("readonly_priority", ReadOnlyPriorityWidget)
            .add("readonly_state_selection", ReadOnlyStateSelectionWidget);
    
    });
