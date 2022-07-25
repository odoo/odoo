odoo.define('board.AddToBoardMenu', function (require) {
    "use strict";

    const Context = require('web.Context');
    const Domain = require('web.Domain');
    const FavoriteMenu = require('web.FavoriteMenu');
    const { sprintf } = require('web.utils');
    const { useAutofocus } = require('web.custom_hooks');

    const { Component, useState } = owl;

    /**
     * 'Add to board' menu
     *
     * Component consisiting of a toggle button, a text input and an 'Add' button.
     * The first button is simply used to toggle the component and will determine
     * whether the other elements should be rendered.
     * The input will be given the name (or title) of the view that will be added.
     * Finally, the last button will send the name as well as some of the action
     * properties to the server to add the current view (and its context) to the
     * user's dashboard.
     * This component is only available in actions of type 'ir.actions.act_window'.
     */
    class AddToBoardMenu extends Component {
        constructor() {
            super(...arguments);

            this.interactive = true;
            this.state = useState({
                name: this.env.action.name || "",
                open: false,
            });

            useAutofocus();
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * This is the main function for actually saving the dashboard.  This method
         * is supposed to call the route /board/add_to_dashboard with proper
         * information.
         * @private
         */
        async addToBoard() {
            const searchQuery = this.env.searchModel.get('query');
            const context = new Context(this.env.action.context);
            context.add(searchQuery.context);
            context.add({
                group_by: searchQuery.groupBy,
                orderedBy: searchQuery.orderedBy,
            });
            if (searchQuery.timeRanges && searchQuery.timeRanges.hasOwnProperty('fieldName')) {
                context.add({
                    comparison: searchQuery.timeRanges,
                });
            }
            let controllerQueryParams;
            this.env.searchModel.trigger('get-controller-query-params', params => {
                controllerQueryParams = params || {};
            });
            controllerQueryParams.context = controllerQueryParams.context || {};
            const queryContext = controllerQueryParams.context;
            delete controllerQueryParams.context;
            context.add(Object.assign(controllerQueryParams, queryContext));

            const domainArray = new Domain(this.env.action.domain || []);
            const domain = Domain.prototype.normalizeArray(domainArray.toArray().concat(searchQuery.domain));

            const evalutatedContext = context.eval();
            for (const key in evalutatedContext) {
                if (evalutatedContext.hasOwnProperty(key) && /^search_default_/.test(key)) {
                    delete evalutatedContext[key];
                }
            }
            evalutatedContext.dashboard_merge_domains_contexts = false;

            Object.assign(this.state, {
                name: $(".o_input").val() || "",
                open: false,
            });

            const result = await this.rpc({
                route: '/board/add_to_dashboard',
                params: {
                    action_id: this.env.action.id || false,
                    context_to_save: evalutatedContext,
                    domain: domain,
                    view_mode: this.env.view.type,
                    name: this.state.name,
                },
            });
            if (result) {
                this.env.services.notification.notify({
                    title: sprintf(this.env._t("'%s' added to dashboard"), this.state.name),
                    message: this.env._t("Please refresh your browser for the changes to take effect."),
                    type: 'warning',
                });
            } else {
                this.env.services.notification.notify({
                    message: this.env._t("Could not add filter to dashboard"),
                    type: 'danger',
                });
            }
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        onInputKeydown(ev) {
            switch (ev.key) {
                case 'Enter':
                    ev.preventDefault();
                    this.addToBoard();
                    break;
                case 'Escape':
                    // Gives the focus back to the component.
                    ev.preventDefault();
                    ev.target.blur();
                    break;
            }
        }

        //---------------------------------------------------------------------
        // Static
        //---------------------------------------------------------------------

        /**
         * @param {Object} env
         * @returns {boolean}
         */
        static shouldBeDisplayed(env) {
            return env.action.type === 'ir.actions.act_window';
        }
    }

    AddToBoardMenu.props = {};
    AddToBoardMenu.template = 'board.AddToBoard';

    FavoriteMenu.registry.add('add-to-board-menu', AddToBoardMenu, 10);

    return AddToBoardMenu;
});
