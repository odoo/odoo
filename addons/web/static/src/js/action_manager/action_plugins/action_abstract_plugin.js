odoo.define('web.ActionAbstractPlugin', function (require) {
    "use_strict";

    class ActionAbstractPlugin {
        constructor(actionManager, env) {
            this.actionManager = actionManager;
            this.env = env;
        }
        //----------------------------------------------------------------------
        // API
        //----------------------------------------------------------------------
        /**
         * @throws {Error} message: Plugin Error
         */
        async executeAction(/*action, options*/) {
            throw new Error(`ActionAbstractPlugin for type ${this.type} doesn't implement executeAction.`);
        }
        loadState(/* state, options */) {}

        //----------------------------------------------------------------------
        // Getters
        // Shorthands to ActionManager's state
        //----------------------------------------------------------------------
        get actions() {
            return this.actionManager.actions;
        }
        get controllers() {
            return this.actionManager.controllers;
        }
        get currentStack() {
            return this.actionManager.currentStack;
        }
        get currentDialogController() {
            return this.actionManager.currentDialogController;
        }

        //----------------------------------------------------------------------
        // Public
        // Normalized shorthands to ActionManager's methods
        //----------------------------------------------------------------------
        doAction() {
            return this.actionManager.doAction(...arguments);
        }
        makeBaseController() {
            return this.actionManager.makeBaseController(...arguments);
        }
        pushControllers() {
            return this.actionManager.pushControllers(...arguments);
        }
        rpc() {
            return this.transactionAdd(this.env.services.rpc(...arguments));
        }
        transactionAdd() {
            return this.actionManager._transaction.add(...arguments);
        }
    }
    ActionAbstractPlugin.type = null;

    return ActionAbstractPlugin;
});