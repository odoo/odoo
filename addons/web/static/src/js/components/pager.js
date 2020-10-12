odoo.define('web.Pager', function (require) {
    "use strict";

    const { useAutofocus } = require('web.custom_hooks');
    const { confine } = require("web.utils");

    const { Component, useState } = owl;

    /**
     * Pager
     *
     * The pager goes from 1 to size (included).
     * The current value is currentMinimum if limit === 1 or the interval:
     *      [currentMinimum, currentMinimum + limit[ if limit > 1].
     * The value can be manually changed by clicking on the pager value and giving
     * an input matching the pattern: min[,max] (in which the comma can be a dash
     * or a semicolon).
     * The pager also provides two buttons to quickly change the current page (next
     * or previous).
     * @extends Component
     */
    class Pager extends Component {
        /**
         * @param {Object} [props]
         * @param {int} [props.size] the total number of elements
         * @param {int} [props.currentMinimum] the first element of the current_page
         * @param {int} [props.limit] the number of elements per page
         * @param {boolean} [props.editable] editable feature of the pager
         * @param {function} [props.validate] callback returning a Promise to
         *   validate changes
         * @param {boolean} [props.withAccessKey] can be disabled, for example,
         *   for x2m widgets
         */
        constructor() {
            super(...arguments);

            useAutofocus();
            this.state = useState({ isEditing: false });
            this.props.value.bindComponent();
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @returns {boolean} true iff there is only one page
         */
        get singlePage() {
            const { currentMinimum, limit } = this.props.value.get();
            const maximum = Math.min(currentMinimum + limit - 1, this.props.size);
            return (1 === currentMinimum) && (maximum === this.props.size);
        }

        /**
         * @returns {string}
         */
        get value() {
            const { currentMinimum, limit } = this.props.value.get();
            const maximum = Math.min(currentMinimum + limit - 1, this.props.size);
            return currentMinimum + (maximum > currentMinimum ? `-${maximum}` : '');
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * Update the pager's state according to a pager action
         * @private
         * @param {number} direction the action (previous or next) on the pager
         */
        async _changeSelection(direction) {
            try {
                await this.props.validate();
            } catch (err) {
                return;
            }
            const { currentMinimum, limit } = this.props.value.get();

            // Compute the new currentMinimum
            let newMinimum = currentMinimum + limit * direction;
            if (newMinimum > this.props.size) {
                newMinimum = 1;
            } else if ((newMinimum < 1) && (limit === 1)) {
                newMinimum = this.props.size;
            } else if ((newMinimum < 1) && (limit > 1)) {
                newMinimum = this.props.size - ((this.props.size % limit) || limit) + 1;
            }

            this.props.value.update({ currentMinimum: newMinimum, limit });
        }

        /**
         * Save the state from the content of the input
         * @private
         * @param {string} value the new raw pager value
         * @returns {Promise}
         */
        async _saveValue(value) {
            try {
                await this.props.validate();
            } catch (err) {
                return;
            }
            const { size } = this.props;
            const [min, max] = value.trim()
                .split(/\s*[\-\s,;]\s*/)
                .map(val => parseInt(val, 10));

            if (isNaN(min) || (max !== undefined && isNaN(max))) {
                return;
            }

            const minimum = confine(min, 1, size);
            const maximum = max ? confine(max, minimum, size) : minimum;

            this.state.isEditing = false;
            this.props.value.update({
                currentMinimum: minimum,
                limit: maximum - minimum + 1,
            });
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        _onEdit() {
            if (this.props.editable && !this.props.value.isLocked) {
                this.state.isEditing = true;
            }
        }

        /**
         * @private
         * @param {InputEvent} ev
         */
        _onValueChange(ev) {
            ev.preventDefault();
            this._saveValue(ev.currentTarget.value);
        }

        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onValueKeydown(ev) {
            switch (ev.key) {
                case 'Enter':
                    ev.preventDefault();
                    ev.stopPropagation();
                    this._saveValue(ev.currentTarget.value);
                    break;
                case 'Escape':
                    ev.preventDefault();
                    ev.stopPropagation();
                    this.state.isEditing = false;
                    break;
            }
        }
    }

    Pager.defaultProps = {
        editable: true,
        validate: async () => { },
        withAccessKey: true,
    };
    Pager.props = {
        value: {
            type: Object,
            shape: {
                bindComponent: Function,
                get: Function,
                isLocked: Boolean,
                update: Function,
            },
        },
        editable: Boolean,
        size: Number,
        validate: Function,
        withAccessKey: Boolean,
    };
    Pager.template = 'web.Pager';

    return Pager;
});
