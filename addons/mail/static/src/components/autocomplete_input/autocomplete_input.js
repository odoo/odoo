/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onWillPatch, onWillUnmount } = owl;

export class AutocompleteInput extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'AutocompleteInputView' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'AutocompleteInputView' });
        onMounted(() => this._mounted());
        onWillPatch(() => this._willPatch());
        onWillUnmount(() => this._willUnmount());
    }

    _mounted() {
        let args = {
            autoFocus: true,
            select: this.autocompleteInputView.onSelect,
            source: this.autocompleteInputView.onSource,
            /**
             * Prevent default behavior of ui-autocomplete
             * to replace content of input by focused item.
             */
            focus: ev => ev.preventDefault(),
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

    _willPatch() {
        if (!this.autocompleteInputView) {
            this._rootEl = this.root.el;
        }
    }

    _willUnmount() {
        if (this._rootEl) {
            $(this._rootEl).autocomplete('destroy');
        } else {
            $(this.root.el).autocomplete('destroy');
        }
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

}

Object.assign(AutocompleteInput, {
    props: { localId: String },
    template: 'mail.AutocompleteInput',
});

registerMessagingComponent(AutocompleteInput);
