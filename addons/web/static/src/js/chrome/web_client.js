odoo.define('web.WebClient', function (require) {
"use strict";

const ActionManager = require('web.ActionManager');
const ActionAdapter = require('web.ActionAdapter');
const { ComponentAdapter } = require('web.OwlCompatibility');
const DialogAction = require('web.DialogAction');
const LoadingWidget = require('web.Loading');
const Menu = require('web.Menu');
const RainbowMan = require('web.RainbowMan');
const LegacyDialog = require('web.Dialog');
const WarningDialog = require('web.CrashManager').WarningDialog;

const { Component, hooks } = owl;
const useRef = hooks.useRef;

class WebClient extends Component {
    constructor() {
        super();
        this.LoadingWidget = LoadingWidget;

        this.currentControllerComponent = useRef('currentControllerComponent');
        this.currentDialogComponent = useRef('currentDialogComponent');
        this.menu = useRef('menu');
        this._setActionManager();

        // the state of the webclient contains information like the current
        // menu id, action id, view type (for act_window actions)...
        this.ignoreHashchange = false;
        this.state = {};

        this.env.bus.on('show-effect', this, this._showEffect);
        this.env.bus.on('connection_lost', this, this._onConnectionLost);
        this.env.bus.on('connection_restored', this, this._onConnectionRestored);

        this.renderingInfo = null;
        this.controllerComponentMap = new Map();
    }
    _setActionManager() {
        this.actionManager = new ActionManager(this.env);
        this.actionManager.on('cancel', this, () => {
            if (this.renderingInfo) {
                this.__owl__.currentFiber.cancel();
            }
        });
        this.actionManager.on('update', this, this._onActionManagerUpdated);
        this.actionManager.on('clear-uncommitted-changes', this, async (callBack) => {
            if (!this.currentDialogComponent.comp && this.currentControllerComponent.comp) {
                await this.currentControllerComponent.comp.canBeRemoved();
            }
            callBack();
        });
        this.actionManager.on('controller-cleaned', this, (controllerIds) => {
            for (const jsID of controllerIds) {
                const comp = this.controllerComponentMap.get(jsID);
                this.controllerComponentMap.delete(jsID);
                if (comp) {
                    comp.destroy(true);
                }
            }
        });
    }
    get titleParts() {
        this._titleParts = this._titleParts || {};
        return this._titleParts;
    }
    // TODO: handle set_title* events
    setTitlePart(part, title) {
        this.titleParts[part] = title;
    }

    async willStart() {
        this.menus = await this._loadMenus();
        const state = this._getUrlState();
        this._determineCompanyIds(state);
        return this.loadState(state);
    }
    async loadState(state) {
        let stateLoaded = await this.actionManager.loadState(state, { menuID: state.menu_id });
        if (stateLoaded === null) {
            if ('menu_id' in state) {
                const action = this.menus[state.menu_id].actionID;
                return this.actionManager.doAction(action, state);
            } else if (('home' in state || Object.keys(state).filter(key => key !== 'cids').length === 0)) {
                const menuID = this.menus ? this.menus.root.children[0] : null;
                const actionID =  menuID ? this.menus[menuID].actionID : null;
                if (actionID) {
                    return this.actionManager.doAction(actionID, {menuID, clear_breadcrumbs: true});
                }
            }
        }
        return stateLoaded;
    }
    mounted() {
        this._onHashchange = () => {
            if (!this.ignoreHashchange) {
                const state = this._getUrlState();
                this.loadState(state);
            }
            this.ignoreHashchange = false;
            // TODO: reset oldURL in case of failure?
        };
        window.addEventListener('hashchange', this._onHashchange);
        super.mounted();
        this._wcUpdated();
        odoo.isReady = true;
        this.env.bus.trigger('web-client-mounted');
    }
    willPatch() {
        super.willPatch();
        const scrollPosition = this._getScrollPosition();
        this._storeScrollPosition(scrollPosition);
    }
    patched() {
        super.patched();
        this._wcUpdated();
    }

    catchError(e) {
        if (e && e.name) {
            // Real runtime error
            throw e;
        }
        // Errors that have been handled before
        console.warn(e);
        if (this.renderingInfo) {
            const newStack = this.renderingInfo.controllerStack;
            const newDialog = this.renderingInfo.dialog;
            this.actionManager.rollBack(newStack, newDialog);
        }
        this.actionManager.restoreController();
    }
    willUnmount() {
        window.removeEventListener('hashchange', this._onHashchange);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    _getWindowHash() {
        return window.location.hash;
    }
    _setWindowHash(newHash) {
        this.ignoreHashchange = true;
        window.location.hash = newHash;
    }
    /**
     * @private
     * @returns {Object}
     */
    _getUrlState() {
        const hash = this._getWindowHash();
        const hashParts = hash ? hash.substr(1).split("&") : [];
        const state = {};
        for (const part of hashParts) {
            const [ key, val ] = part.split('=');
            let decodedVal;
            if (val === undefined) {
                decodedVal = '1';
            } else {
                decodedVal = decodeURI(val);
            }
            state[key] = isNaN(decodedVal) ? decodedVal : parseInt(decodedVal, 10);
        }

        return state;
    }
    _determineCompanyIds(state) {
        const userCompanies = this.env.session.user_companies;
        const currentCompanyId = userCompanies.current_company[0];
        if (!state.cids) {
            state.cids = this.env.services.getCookie('cids') || currentCompanyId;
        }
        let stateCompanyIds = state.cids.toString().split(',').map(id => parseInt(id, 10));
        const userCompanyIds = userCompanies.allowed_companies.map(company => company[0]);
        // Check that the user has access to all the companies
        if (!_.isEmpty(_.difference(stateCompanyIds, userCompanyIds))) {
            state.cids = String(currentCompanyId);
            stateCompanyIds = [currentCompanyId];
        }
        this.env.session.user_context.allowed_company_ids = stateCompanyIds;
    }
    _displayNotification(params) {
        const notifService = this.env.services.notification;
        return notifService.notify(params);
    }
    /**
     * FIXME: consider moving this to menu.js
     * Loads and sanitizes the menu data
     *
     * @private
     * @returns {Promise<Object>}
     */
    _loadMenus() {
        if (!odoo.loadMenusPromise) {
            throw new Error('can we get here? tell aab if so');
        }
        const loadMenusPromise = odoo.loadMenusPromise || odoo.reloadMenus();
        return loadMenusPromise.then(menuData => {
            // set action if not defined on top menu items
            for (let app of menuData.children) {
                let child = app;
                while (app.action === false && child.children.length) {
                    child = child.children[0];
                    app.action = child.action;
                }
            }
            const menus = {};
            function processMenu(menu, appID) {
                appID = appID || menu.id;
                for (let submenu of menu.children) {
                    processMenu(submenu, appID);
                }
                const action = menu.action && menu.action.split(',');
                const menuID = menu.id || 'root';
                menus[menuID] = {
                    id: menuID,
                    appID: appID,
                    name: menu.name,
                    children: menu.children.map(submenu => submenu.id),
                    actionModel: action ? action[0] : false,
                    actionID: action ? parseInt(action[1], 10) : false,
                    xmlid: menu.xmlid,
                };
            }
            processMenu(menuData);

            odoo.loadMenusPromise = null;
            return menus;
        });
    }
    /**
     * @private
     * @param {Object} state
     */
    _updateState(state) {
        // the action and menu_id may not have changed
        state.action = state.action || this.state.action || '';
        const menuID = state.menu_id || this.state.menu_id || '';
        if (menuID) {
            state.menu_id = menuID;
        }
        if ('title' in state) {
            this.setTitlePart('action', state.title);
            delete state.title
        }
        this.state = state;
        const hashParts = Object.keys(state).map(key => {
            const value = state[key];
            if (value !== null) {
                return `${key}=${encodeURI(value)}`;
            }
            return '';
        });
        const hash = "#" + hashParts.join("&");
        if (hash !== this._getWindowHash()) {
            this._setWindowHash(hash);
        }
        const fullTitle = this._computeTitle();
        this._setWindowTitle(fullTitle);
    }
    _onActionManagerUpdated(payload) {
        const { controllerStack, dialog, onCommit, doOwlReload } = payload;
        const breadcrumbs = [];
        let fullscreen = false;
        let menuID;
        controllerStack.forEach((elm, index) =>{
            const controller = elm.controller;
            menuID = controller.options && controller.options.menuID || menuID;
            if (elm.action.target === 'fullscreen') {
                fullscreen = true;
            }
            const component = this.controllerComponentMap.get(controller.jsID);
            breadcrumbs.push({
                controllerID: controller.jsID,
                title: component && component.title || elm.action.name,
            });
            controller.viewOptions = controller.viewOptions || {};
            controller.viewOptions.breadcrumbs = breadcrumbs.slice(0, index);
        });
        const main = controllerStack[controllerStack.length - 1];
        if (!menuID) {
            if (this.state.menu_id) {
                menuID = this.state.menu_id;
            } else if (main) {
                const menu = Object.values(this.menus).find(menu => {
                    return menu.actionID === main.action.id;
                });
                menuID = menu && menu.id;
            }
        }
        if (main) {
            main.reload = doOwlReload !== undefined ? doOwlReload && !dialog : !dialog;
        }
        this.renderingInfo = {
            main, dialog, menuID, fullscreen,
            controllerStack, onCommit
        };
        this._domCleaning();
        this.render();
    }
    _wcUpdated() {
        if (this.renderingInfo) {
            let state = {};
            if (this.renderingInfo.main) {
                const main = this.renderingInfo.main;
                const mainComponent = this.currentControllerComponent.comp;
                this.controllerComponentMap.set(main.controller.jsID, mainComponent);
                Object.assign(state, mainComponent.getState());
                state.action = main.action.id;
                let active_id = null;
                let active_ids = null;
                if (main.action.context) {
                    active_id = main.action.context.active_id || null;
                    active_ids = main.action.context.active_ids;
                    if (active_ids && !(active_ids.length === 1 && active_ids[0] === active_id)) {
                        active_ids = active_ids.join(',');
                    } else {
                        active_ids = null;
                    }
                }
                if (active_id) {
                    state.active_id = active_id;
                }
                if (active_ids) {
                    state.active_ids = active_ids;
                }
                if (!('title' in state)) {
                    state.title = mainComponent.title;
                }
                // keep cids in hash
                //this._determineCompanyIds(state);
                const scrollPosition = this.renderingInfo.main.controller.scrollPosition;
                if (scrollPosition) {
                    this._scrollTo(scrollPosition);
                }
            }
            if (this.renderingInfo.dialog) {
                this.controllerComponentMap.set(this.renderingInfo.dialog.controller.jsID, this.currentDialogComponent.comp);
            }
            const newStack = this.renderingInfo.controllerStack;
            const newDialog = this.renderingInfo.dialog;
            this.actionManager.commit(newStack, newDialog, this.renderingInfo.onCommit);

            if (this.renderingInfo.menuID) {
                state.menu_id = this.renderingInfo.menuID;
            }
            if (!this.renderingInfo.dialog) {
                this._updateState(state);
            }
        }
        this.renderingInfo = null;
        this.env.bus.trigger('web-client-updated', this);
    }
    _domCleaning() {
        const body = document.body;
        // multiple bodies in tests
        const tooltips = body.querySelectorAll('body .tooltip');
        for (let tt of tooltips) {
            tt.parentNode.removeChild(tt);
        }
    }
    _computeTitle() {
        const parts = Object.keys(this.titleParts).sort();
        let tmp = "";
        for (let part of parts) {
            const title = this.titleParts[part];
            if (title) {
                tmp = tmp ? tmp + " - " + title : title;
            }
        }
        return tmp;
    }
    /**
     * Returns the left and top scroll positions of the main scrolling area
     * (i.e. the '.o_content' div in desktop).
     *
     * @private
     * @returns {Object} with keys left and top
     */
    _getScrollPosition() {
        var scrollingEl = this.el.getElementsByClassName('o_content')[0];
        return {
            left: scrollingEl ? scrollingEl.scrollLeft : 0,
            top: scrollingEl ? scrollingEl.scrollTop : 0,
        };
    }
    _storeScrollPosition(scrollPosition) {
        const cStack = this.renderingInfo.controllerStack;
        const { controller } = cStack[cStack.length-2] || {};
        if (controller) {
            controller.scrollPosition = scrollPosition;
        }
    }
    _setWindowTitle(title) {
        document.title = title;
    }
    _getWindowTitle() {
        return document.title;
    }
    _scrollTo(scrollPosition) {
        const scrollingEl = this.el.getElementsByClassName('o_content')[0];
        if (!scrollingEl) {
            return;
        }
        scrollingEl.scrollTop = scrollPosition.top || 0;
        scrollingEl.scrollLeft = scrollPosition.left || 0;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onOpenMenu(ev) {
        const action = this.menus[ev.detail.menuID].actionID;
        this.actionManager.doAction(action, {
            clear_breadcrumbs: true,
            menuID: ev.detail.menuID,
        });
    }
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.detail.controllerID
     */
    _onBreadcrumbClicked(ev) {
        this.actionManager.restoreController(ev.detail.controllerID);
    }
    /**
     * Whenever the connection is lost, we need to notify the user.
     *
     * @private
     */
    _onConnectionLost() {
        this.connectionNotificationID = this._displayNotification({
            title: this.env._t('Connection lost'),
            message: this.env._t('Trying to reconnect...'),
            sticky: true
        });
    }
    /**
     * Whenever the connection is restored, we need to notify the user.
     *
     * @private
     */
    _onConnectionRestored() {
        if (this.connectionNotificationID) {
            this.env.services.notification.close(this.connectionNotificationID);
            this._displayNotification({
                type: 'info',
                title: this.env._t('Connection restored'),
                message: this.env._t('You are back online'),
                sticky: false
            });
            this.connectionNotificationID = false;
        }
    }
    _onDialogClosed() {
        this.actionManager.doAction({type: 'ir.actions.act_window_close'});
    }
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.detail
     */
    _onExecuteAction(ev) {
        this.actionManager.executeInFlowAction(ev.detail);
    }
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.detail.state
     */
    _onPushState(ev) {
        if (!this.renderingInfo) {
            // Deal with that event only if we are not in a rendering cycle
            // i.e.: the rendering cycle will update the state at its end
            // Any event hapening in the meantime would be irrelevant
            this._updateState(ev.detail.state);
        }
    }
    _showEffect(params) {
        params = params || {};
        const type = params.type || 'rainbow_man';
        if (type === 'rainbow_man') {
            if (this.env.session.show_effect) {
                RainbowMan.display(params, {target: this.el, parent: this});
            } else {
                // For instance keep title blank, as we don't have title in data
                this._displayNotification({
                    title: "",
                    message: params.message,
                    sticky: false
                });
            }
        } else {
            throw new Error('Unknown effect type: ' + type);
        }
    }
    /**
     * Displays a visual effect (for example, a rainbowMan0
     *
     * @private
     * @param {OdooEvent} ev
     * @param {Object} [ev.data] - key-value options to decide rainbowMan
     *   behavior / appearance
     */
    _onShowEffect(ev) {
        if (!this.renderingInfo) {
            const params = ev.detail;
            this._showEffect(params);
        }
    }
    /**
     * Displays a warning in a dialog or with the notification service
     *
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.data.message the warning's message
     * @param {string} ev.data.title the warning's title
     * @param {string} [ev.data.type] 'dialog' to display in a dialog
     * @param {boolean} [ev.data.sticky] whether or not the warning should be
     *   sticky (if displayed with the Notification)
     */
    _onDisplayWarning(ev) {
        var data = ev.detail;
        if (data.type === 'dialog') {
            const warningDialog = new LegacyDialog.DialogAdapter(this,
                {
                    Component: WarningDialog,
                    widgetArgs: {
                        options: {title: data.title},
                        error: data
                    },
                }
            );
            warningDialog.mount(this.el.querySelector('.o_dialogs'));
        } else {
            data.type = 'warning';
            this._displayNotification(data);
        }
    }
}
WebClient.components = { ActionAdapter, Menu, DialogAction, ComponentAdapter };
WebClient.template = 'web.WebClient';

return WebClient;

});
