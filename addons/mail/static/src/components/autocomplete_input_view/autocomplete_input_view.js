/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onWillUnmount } = owl;

export class AutocompleteInput extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        onMounted(() => this._mounted());
        onWillUnmount(() => this._willUnmount());
    }

    _mounted() {
        if (!this.root.el) {
            return;
        }
        if (this.autocompleteInputView.isFocusOnMount) {
            this.root.el.focus();
        }

        let args = {
            autoFocus: true,
            select: (ev, ui) => this._onAutocompleteSelect(ev, ui),
            source: (req, res) => this._onAutocompleteSource(req, res),
            focus: ev => this._onAutocompleteFocus(ev),
            html: this.autocompleteInputView.isHtml,
        };

        if (this.autocompleteInputView.customClass) {
            args.classes = { 'ui-autocomplete': this.autocompleteInputView.customClass };
        }

        const autoCompleteElem = $(this.root.el).autocomplete(args);
        // Resize the autocomplete dropdown options to handle the long strings
        // By setting the width of dropdown based on the width of the input element.
        autoCompleteElem.data("ui-autocomplete")._resizeMenu = function () {
            const ul = this.menu.element;
            ul.outerWidth(this.element.outerWidth());
        };
    }

    _willUnmount() {
        if (!this.root.el) {
            return;
        }
        $(this.root.el).autocomplete('destroy');
    }

    /**
     * @returns {AutocompleteInputView}
     */
     get autocompleteInputView() {
        return this.props.record;
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
        if (!this.root.el) {
            return false;
        }
        if (this.root.el.contains(node)) {
            return true;
        }
        if (!this.autocompleteInputView.customClass) {
            return false;
        }
        const element = document.querySelector(`.${this.autocompleteInputView.customClass}`);
        if (!element) {
            return false;
        }
        return element.contains(node);
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
        if (this.messaging) {
            this.messaging.messagingBus.trigger('o-AutocompleteInput-source', {});
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onBlur(ev) {
        if (this.props.onHide) {
            this.props.onHide();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onKeydown(ev) {
        if (ev.key === 'Escape') {
            if (this.props.onHide) {
                this.props.onHide();
            }
        }
    }

}

Object.assign(AutocompleteInput, {
    props: {
        focus: {
            type: Function,
            optional: true,
        },
        record: Object,
        onHide: {
            type: Function,
            optional: true,
        },
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
