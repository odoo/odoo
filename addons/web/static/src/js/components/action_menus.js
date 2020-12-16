odoo.define('web.ActionMenus', function (require) {
    "use strict";

    const Context = require('web.Context');
    const DropdownMenu = require('web.DropdownMenu');
    const Registry = require('web.Registry');

    const { Component } = owl;

    let registryActionId = 1;

    /**
     * Action menus (or Action/Print bar, previously called 'Sidebar')
     *
     * The side bar is the group of dropdown menus located on the left side of the
     * control panel. Its role is to display a list of items depending on the view
     * type and selected records and to execute a set of actions on active records.
     * It is made out of 2 dropdown menus: Print and Action.
     *
     * This component also provides a registry to use custom components in the ActionMenus's
     * Action menu.
     * @extends Component
     */
    class ActionMenus extends Component {

        async willStart() {
            this.actionItems = await this._setActionItems(this.props);
            this.printItems = await this._setPrintItems(this.props);
        }

        async willUpdateProps(nextProps) {
            this.actionItems = await this._setActionItems(nextProps);
            this.printItems = await this._setPrintItems(nextProps);
        }

        mounted() {
            this._addTooltips();
        }

        patched() {
            this._addTooltips();
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * Add the tooltips to the items
         * @private
         */
        _addTooltips() {
            $(this.el.querySelectorAll('[title]')).tooltip({
                delay: { show: 500, hide: 0 }
            });
        }

        /**
         * @private
         * @param {Object} props
         * @returns {Promise<Object[]>}
         */
        async _setActionItems(props) {
            // Callback based actions
            const callbackActions = (props.items.other || []).map(
                action => Object.assign({ key: `action-${action.description}` }, action)
            );
            // Action based actions
            const actionActions = props.items.action || [];
            const relateActions = props.items.relate || [];
            const formattedActions = [...actionActions, ...relateActions].map(
                action => ({ action, description: action.name, key: action.id })
            );
            // ActionMenus action registry components
            const registryActions = [];
            const rpc = this.rpc.bind(this);
            for (const { Component, getProps } of this.constructor.registry.values()) {
                const itemProps = await getProps(props, this.env, rpc);
                if (itemProps) {
                    registryActions.push({
                        Component,
                        key: `registry-action-${registryActionId++}`,
                        props: itemProps,
                    });
                }
            }

            return [...callbackActions, ...formattedActions, ...registryActions];
        }

        /**
         * @private
         * @param {Object} props
         * @returns {Promise<Object[]>}
         */
        async _setPrintItems(props) {
            const printActions = props.items.print || [];
            const printItems = printActions.map(
                action => ({ action, description: action.name, key: action.id })
            );
            return printItems;
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * Perform the action for the item clicked after getting the data
         * necessary with a trigger.
         * @private
         * @param {OwlEvent} ev
         */
        async _executeAction(action) {
            let activeIds = this.props.activeIds;
            if (this.props.isDomainSelected) {
                activeIds = await this.rpc({
                    model: this.env.action.res_model,
                    method: 'search',
                    args: [this.props.domain],
                    kwargs: {
                        limit: this.env.session.active_ids_limit,
                    },
                });
            }
            const activeIdsContext = {
                active_id: activeIds[0],
                active_ids: activeIds,
                active_model: this.env.action.res_model,
            };
            if (this.props.domain) {
                // keep active_domain in context for backward compatibility
                // reasons, and to allow actions to bypass the active_ids_limit
                activeIdsContext.active_domain = this.props.domain;
            }

            const context = new Context(this.props.context, activeIdsContext).eval();
            const result = await this.rpc({
                route: '/web/action/load',
                params: { action_id: action.id, context },
            });
            result.context = new Context(result.context || {}, activeIdsContext)
                .set_eval_context(context);
            result.flags = result.flags || {};
            result.flags.new_window = true;
            this.trigger('do-action', {
                action: result,
                options: {
                    on_close: () => this.trigger('reload'),
                },
            });
        }

        /**
         * Handler used to determine which way must be used to execute a selected
         * action: it will be either:
         * - a callback (function given by the view controller);
         * - an action ID (string);
         * - an URL (string).
         * @private
         * @param {OwlEvent} ev
         */
        _onItemSelected(ev) {
            ev.stopPropagation();
            const { item } = ev.detail;
            if (item.callback) {
                item.callback([item]);
            } else if (item.action) {
                this._executeAction(item.action);
            } else if (item.url) {
                // Event has been prevented at its source: we need to redirect manually.
                this.env.services.navigate(item.url);
            }
        }
    }

    ActionMenus.registry = new Registry();

    ActionMenus.components = { DropdownMenu };
    ActionMenus.props = {
        activeIds: { type: Array, element: [Number, String] }, // virtual IDs are strings.
        context: Object,
        domain: { type: Array, optional: 1 },
        isDomainSelected: { type: Boolean, optional: 1 },
        items: {
            type: Object,
            shape: {
                action: { type: Array, optional: 1 },
                print: { type: Array, optional: 1 },
                other: { type: Array, optional: 1 },
            },
        },
    };
    ActionMenus.template = 'web.ActionMenus';

    return ActionMenus;
});
