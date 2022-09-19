/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onWillUnmount } = owl;

export class AutocompleteInputView extends Component {

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

        const args = {
            autoFocus: true,
            select: (ev, ui) => {
                if (this.autocompleteInputView) {
                    this.autocompleteInputView.onSelect(ev, ui);
                }
            },
            source: (req, res) => {
                if (this.autocompleteInputView) {
                    this.autocompleteInputView.onSource(req, res);
                }
            },
            html: this.autocompleteInputView.isHtml,
        };

        if (this.autocompleteInputView.customClass) {
            args.classes = { 'ui-autocomplete': this.autocompleteInputView.customClass };
        }

        const autoCompleteElem = $(this.root.el).autocomplete(args);
        // Resize the autocomplete dropdown options to handle the long strings
        // By setting the width of dropdown based on the width of the input element.
        autoCompleteElem.data('ui-autocomplete')._resizeMenu = function () {
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

}

Object.assign(AutocompleteInputView, {
    props: { record: Object },
    template: 'mail.AutocompleteInputView',
});

registerMessagingComponent(AutocompleteInputView);
