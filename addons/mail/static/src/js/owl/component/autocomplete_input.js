odoo.define('mail.component.AutocompleteInput', function () {
'use strict';

class AutocompleteInput extends owl.Component {

    mounted() {
        if (this.props.isFocusOnMount) {
            this.el.focus();
        }

        let args = {
            select: (ev, ui) => this._onAutocompleteSelect(ev, ui),
            source: (req, res) => this._onAutocompleteSource(req, res),
            focus: ev => this._onAutocompleteFocus(ev),
            html: this.props.isHtml || false,
        };

        if (this.props.customClass) {
            args.classes = {
                'ui-autocomplete': this.props.customClass,
            };
        }

        $(this.el).autocomplete(args);
    }

    willUnmount() {
        $(this.el).autocomplete('destroy');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    focus() {
        if (!this.el) {
            return;
        }
        this.el.focus();
    }

    focusout() {
        if (!this.el) {
            return;
        }
        this.el.blur();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {FocusEvent} ev
     */
    _onAutocompleteFocus(ev) {
        if (this.props.focus) {
            this.props.focus(ev);
        } else {
            ev.preventDefault();
        }
    }

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     */
    _onAutocompleteSelect(ev, ui) {
        ev.stopPropagation();
        if (this.props.select) {
            this.props.select(ev, ui);
        }
    }

    /**
     * @private
     * @param {Object} req
     * @param {function} res
     */
    _onAutocompleteSource(req, res) {
        if (this.props.source) {
            this.props.source(req, res);
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onBlur(ev) {
        this.trigger('o-hide');
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onKeydown(ev) {
        if (ev.key === 'Escape') {
            this.trigger('o-hide');
        }
    }
}

AutocompleteInput.defaultProps = {
    isFocusOnMount: false,
    isHtml: false,
    placeholder: '',
};

AutocompleteInput.props = {
    customClass: {
        type: String,
        optional: true,
    },
    focus: {
        type: Function,
        optional: true,
    },
    isFocusOnMount: Boolean,
    isHtml: Boolean,
    placeholder: String,
    select: {
        type: Function,
        optional: true,
    },
    source: {
        type: Function,
        optional: true,
    },
};

AutocompleteInput.template = 'mail.component.AutocompleteInput';

return AutocompleteInput;

});
