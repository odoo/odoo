/** @odoo-module alias=web.AbstractRenderer **/

/**
 * The renderer should not handle pagination, data loading, or coordination
 * with the control panel. It is only concerned with rendering.
 *
 */

import { renderToString } from '@web/core/utils/render';
import * as mvc from 'web.mvc';

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

/**
 * @class AbstractRenderer
 */
export default mvc.Renderer.extend({
    // Defines the elements suppressed when in demo data. This must be a list
    // of DOM selectors matching view elements that will:
    // 1. receive the 'o_sample_data_disabled' class (greyd out & no user events)
    // 2. have themselves and any of their focusable children removed from the
    //    tab navigation
    sampleDataTargets: [],

    /**
     * @override
     * @param {string} [params.noContentHelp]
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.arch = params.arch;
        this.noContentHelp = params.noContentHelp;
        this.withSearchPanel = params.withSearchPanel;
    },
    /**
     * The rendering is asynchronous. The start
     * method simply makes sure that we render the view.
     *
     * @returns {Promise}
     */
    async start() {
        this.$el.addClass(this.arch.attrs.class);
        if (this.withSearchPanel) {
            this.$el.addClass('o_renderer_with_searchpanel');
        }
        await Promise.all([this._render(), this._super()]);
    },
    /**
     * Called each time the renderer is attached into the DOM.
     */
    on_attach_callback: function () {},
    /**
     * Called each time the renderer is detached from the DOM.
     */
    on_detach_callback: function () {},

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns any relevant state that the renderer might want to keep.
     *
     * The idea is that a renderer can be destroyed, then be replaced by another
     * one instantiated with the state from the model and the localState from
     * the renderer, and the end result should be the same.
     *
     * The kind of state that we expect the renderer to have is mostly DOM state
     * such as the scroll position, the currently active tab page, ...
     *
     * This method is called before each updateState, by the controller.
     *
     * @see setLocalState
     * @returns {any}
     */
    getLocalState: function () {
    },
    /**
     * Order to focus to be given to the content of the current view
     */
    giveFocus: function () {
    },
    /**
     * Resets state that renderer keeps, state may contains scroll position,
     * the currently active tab page, ...
     *
     * @see getLocalState
     * @see setLocalState
     */
    resetLocalState() {
    },
    /**
     * This is the reverse operation from getLocalState.  With this method, we
     * expect the renderer to restore all DOM state, if it is relevant.
     *
     * This method is called after each updateState, by the controller.
     *
     * @see getLocalState
     * @param {any} localState the result of a call to getLocalState
     */
    setLocalState: function (localState) {
    },
    /**
     * Updates the state of the view. It retriggers a full rerender, unless told
     * otherwise (for optimization for example).
     *
     * @param {any} state
     * @param {Object} params
     * @param {boolean} [params.noRender=false]
     *        if true, the method only updates the state without rerendering
     * @returns {Promise}
     */
    async updateState(state, params) {
        this._setState(state);
        if (!params.noRender) {
            await this._render();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Renders the widget. This method can be overriden to perform actions
     * before or after the view has been rendered.
     *
     * @private
     * @returns {Promise}
     */
    async _render() {
        await this._renderView();
        this._suppressFocusableElements();
    },
    /**
     * @private
     * @param {Object} [context]
     */
    _renderNoContentHelper: function (context) {
        let templateName;
        if (!context && this.noContentHelp) {
            templateName = "web.ActionHelper";
            context = { noContentHelp: this.noContentHelp };
        } else {
            templateName = "web.NoContentHelper";
        }
        const innerHTML = renderToString(templateName, context);
        const template = Object.assign(document.createElement("template"), { innerHTML });
        this.el.append(template.content.firstChild);
    },
    /**
     * Actual rendering. This method is meant to be overridden by concrete
     * renderers.
     *
     * @abstract
     * @private
     * @returns {Promise}
     */
    async _renderView() { },
    /**
     * Assigns a new state to the renderer if not false.
     *
     * @private
     * @param {any} [state=false]
     */
    _setState(state = false) {
        if (state !== false) {
            this.state = state;
        }
    },
    /**
     * Suppresses 'tabindex' property on any focusable element located inside
     * root elements defined in the `this.sampleDataTargets` object and assigns
     * the 'o_sample_data_disabled' class to these root elements.
     *
     * @private
     * @see sampleDataTargets
     */
    _suppressFocusableElements() {
        if (!this.state.isSample || this.isEmbedded) {
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
    },
});
