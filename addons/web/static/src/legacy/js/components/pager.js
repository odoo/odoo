odoo.define('web.Pager', function (require) {
    "use strict";

    const { useAutofocus } = require("@web/core/utils/hooks");
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    const { onWillUpdateProps, useState } = owl;

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
    class Pager extends LegacyComponent {
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
        setup() {
            this.state = useState({
                disabled: false,
                editing: false,
            });

            useAutofocus();

            onWillUpdateProps(this.onWillUpdateProps);
        }

        async onWillUpdateProps() {
            this.state.editing = false;
            this.state.disabled = false;
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @returns {number}
         */
        get maximum() {
            return Math.min(this.props.currentMinimum + this.props.limit - 1, this.props.size);
        }

        /**
         * @returns {boolean} true iff there is only one page
         */
        get singlePage() {
            return (1 === this.props.currentMinimum) && (this.maximum === this.props.size);
        }

        /**
         * @returns {number}
         */
        get value() {
            return this.props.currentMinimum + (this.props.limit > 1 ? `-${this.maximum}` : '');
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * Update the pager's state according to a pager action
         * @private
         * @param {number} [direction] the action (previous or next) on the pager
         */
        async _changeSelection(direction) {
            try {
                await this.props.validate();
            } catch (_err) {
                return;
            }
            const { limit, size } = this.props;

            // Compute the new currentMinimum
            let currentMinimum = (this.props.currentMinimum + limit * direction);
            if (currentMinimum > size) {
                currentMinimum = 1;
            } else if ((currentMinimum < 1) && (limit === 1)) {
                currentMinimum = size;
            } else if ((currentMinimum < 1) && (limit > 1)) {
                currentMinimum = size - ((size % limit) || limit) + 1;
            }

            // The re-rendering of the pager must be done before the trigger of
            // event 'pager-changed' as the rendering may enable the pager
            // (and a common use is to disable the pager when this event is
            // triggered, and to re-enable it when the data have been reloaded).
            this._updateAndDisable(currentMinimum, limit);
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
            } catch (_err) {
                return;
            }
            const [min, max] = value.trim().split(/\s*[\-\s,;]\s*/);

            let currentMinimum = Math.max(Math.min(parseInt(min, 10), this.props.size), 1);
            let maximum = max ? Math.max(Math.min(parseInt(max, 10), this.props.size), 1) : min;

            if (
                !isNaN(currentMinimum) &&
                !isNaN(maximum) &&
                currentMinimum <= maximum
            ) {
                const limit = Math.max(maximum - currentMinimum) + 1;
                this._updateAndDisable(currentMinimum, limit);
            }
        }

        /**
         * Commits the current input value. There are two scenarios:
         * - the value is the same: the pager toggles back to readonly
         * - the value changed: the pager is disabled to prevent furtherchanges
         * Either way the "pager-changed" event is triggered to reload the
         * view.
         * @private
         * @param {number} currentMinimum
         * @param {number} limit
         */
        _updateAndDisable(currentMinimum, limit) {
            if (
                currentMinimum !== this.props.currentMinimum ||
                limit !== this.props.limit
            ) {
                this.state.disabled = true;
            } else {
                // In this case we want to trigger an update, but since it will
                // not re-render the pager (current props === next props) we
                // have to disable the edition manually here.
                this.state.editing = false;
            }
            this.props.onPagerChanged({ currentMinimum, limit });
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         */
        _onEdit() {
            if (
                this.props.editable && // editable
                !this.state.editing && // not already editing
                !this.state.disabled // not being changed already
            ) {
                this.state.editing = true;
            }
        }

        /**
         * @private
         * @param {InputEvent} ev
         */
        _onValueChange(ev) {
            this._saveValue(ev.currentTarget.value);
            if (!this.state.disabled) {
                ev.preventDefault();
            }
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
                    this.state.editing = false;
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
        currentMinimum: { type: Number, optional: 1 },
        editable: { type: Boolean, optional: true },
        limit: { validate: l => !isNaN(l), optional: 1 },
        size: { type: Number, optional: 1 },
        validate: { type: Function, optional: true },
        withAccessKey: { type: Boolean, optional: true },
        onPagerChanged: Function,
    };
    Pager.template = 'web.legacy.Pager';

    return Pager;
});
