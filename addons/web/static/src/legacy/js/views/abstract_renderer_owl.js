/** @odoo-module alias=web.AbstractRendererOwl **/

import { LegacyComponent } from "@web/legacy/legacy_component";
import { onMounted, onPatched } from "@odoo/owl";

// Renderers may display sample data when there is no real data to display. In
// this case the data is displayed with opacity and can't be clicked. Moreover,
// we also want to prevent the user from accessing DOM elements with TAB
// navigation. This is the list of elements we won't allow to focus.
const FOCUSABLE_ELEMENTS = [
    // focusable by default
    'a', 'button', 'input', 'select', 'textarea',
    // manually set
    '[tabindex="0"]'
].map((sel) => `:scope ${sel}`).join(', ');

class AbstractRenderer extends LegacyComponent {

    setup() {
        // Defines the elements suppressed when in demo data. This must be a list
        // of DOM selectors matching view elements that will:
        // 1. receive the 'o_sample_data_disabled' class (greyd out & no user events)
        // 2. have themselves and any of their focusable children removed from the
        //    tab navigation
        this.sampleDataTargets = [];

        onMounted(() => {
            this._suppressFocusableElements();
        });
        onPatched(() => {
            this._suppressFocusableElements();
        });
    }

    /**
     * Suppresses 'tabindex' property on any focusable element located inside
     * root elements defined in the `this.sampleDataTargets` object and assigns
     * the 'o_sample_data_disabled' class to these root elements.
     *
     * @private
     * @see sampleDataTargets
     */
    _suppressFocusableElements() {
        if (!this.props.isSample || this.props.isEmbedded) {
            const disabledEls = this.el.querySelectorAll(`.o_sample_data_disabled`);
            disabledEls.forEach(el => el.classList.remove('o_sample_data_disabled'));
            return;
        }
        const rootEls = [];
        for (const selector of this.sampleDataTargets) {
            rootEls.push(...this.el.querySelectorAll(`:scope ${selector}`));
        }
        const focusableEls = new Set(rootEls);
        for (const rootEl of rootEls) {
            rootEl.classList.add('o_sample_data_disabled');
            for (const focusableEl of rootEl.querySelectorAll(FOCUSABLE_ELEMENTS)) {
                focusableEls.add(focusableEl);
            }
        }
        for (const focusableEl of focusableEls) {
            focusableEl.setAttribute('tabindex', -1);
            if (focusableEl.classList.contains('dropdown-item')) {
                // Tells Bootstrap to ignore the dropdown item in keynav
                focusableEl.classList.add('disabled');
            }
        }
    }
}

export default AbstractRenderer;
