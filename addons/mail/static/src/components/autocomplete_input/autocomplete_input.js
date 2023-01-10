/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AutocompleteInput extends Component {

    mounted() {
        if (this.props.isFocusOnMount) {
            this.el.focus();
        }

        let args = {
            autoFocus: true,
            select: (ev, ui) => this._onAutocompleteSelect(ev, ui),
            source: (req, res) => this._onAutocompleteSource(req, res),
            focus: ev => this._onAutocompleteFocus(ev),
            html: this.props.isHtml || false,
        };

        if (this.props.customClass) {
            args.classes = { 'ui-autocomplete': this.props.customClass };
        }

        const autoCompleteElem = $(this.el).autocomplete(args);
        // Resize the autocomplete dropdown options to handle the long strings
        // By setting the width of dropdown based on the width of the input element.
        autoCompleteElem.data("ui-autocomplete")._resizeMenu = function () {
            const ul = this.menu.element;
            ul.outerWidth(this.element.outerWidth());
        };
    }

    willUnmount() {
        $(this.el).autocomplete('destroy');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns whether the given node is self or a children of self, including
     * the suggestion menu.
     *
     * @param {Node} node
     * @returns {boolean}
     */
    contains(node) {
        if (!this.el) {
            return false;
        }
        if (this.el.contains(node)) {
            return true;
        }
        if (!this.props.customClass) {
            return false;
        }
        const element = document.querySelector(`.${this.props.customClass}`);
        if (!element) {
            return false;
        }
        return element.contains(node);
    }

    focus() {
        if (!this.el) {
            return;
        }
        this.el.focus();
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

Object.assign(AutocompleteInput, {
    defaultProps: {
        isFocusOnMount: false,
        isHtml: false,
        placeholder: '',
    },
    props: {
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
    },
    template: 'mail.AutocompleteInput',
});

registerMessagingComponent(AutocompleteInput);
