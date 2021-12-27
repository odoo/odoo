/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;
const { onMounted, onWillUnmount } = owl.hooks;

export class AutocompleteInput extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'AutocompleteInputView', propNameAsRecordLocalId: 'localId' });
        onMounted(() => this._mounted());
        onWillUnmount(() => this._willUnmount());
    }

    _mounted() {
        if (this.autocompleteInputView.isFocusOnMount) {
            this.root.el.focus();
        }

        let args = {
            autoFocus: true,
            select: this.autocompleteInputView.select,
            source: this.autocompleteInputView.source,
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
        $(this.root.el).autocomplete('destroy');
    }

    get autocompleteInputView() {
        return this.messaging && this.messaging.models['AutocompleteInputView'].get(this.props.localId);
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
        if (this.autocompleteInputView.focus) {
            this.autocompleteInputView.focus(ev);
        } else {
            ev.preventDefault();
        }
    }

    /**
     * @private
     * @param {Object} req
     * @param {function} res
     */
    _onAutocompleteSource(req, res) {
        if (this.autocompleteInputView.source) {
            this.autocompleteInputView.source(req, res);
        }
    }

}

Object.assign(AutocompleteInput, {
    props: {
        localId: String,
    },
    template: 'mail.AutocompleteInput',
});

registerMessagingComponent(AutocompleteInput);
