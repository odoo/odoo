odoo.define('web.WebClient', function (require) {
"use strict";

const ActionManager = require('web.ActionManager');
const ActionAdapter = require('web.ActionAdapter');
const { useListener } = require('web.custom_hooks');
const { ComponentAdapter } = require('web.OwlCompatibility');
const DialogAction = require('web.DialogAction');
const LoadingWidget = require('web.Loading');
const Menu = require('web.Menu');
const RainbowMan = require('web.RainbowMan');
const LegacyDialog = require('web.Dialog');
const WarningDialog = require('web.CrashManager').WarningDialog;

const { Component, hooks } = owl;
const { useRef, useExternalListener } = hooks;

class WebClient extends Component {
    constructor() {
        super();
        this.LoadingWidget = LoadingWidget;
        useExternalListener(window, 'hashchange', this._onHashchange);
        useListener('click', this._onGenericClick);

        this.currentMainComponent = useRef('currentMainComponent');
        this.currentDialogComponent = useRef('currentDialogComponent');
        this.menu = useRef('menu');
        this._setActionManager();

        // the state of the webclient contains information like the current
        // menu id, action id, view type (for act_window actions)...
        this.ignoreHashchange = false;
        this.state = {};
        this._titleParts = {};

        this.env.bus.on('show-effect', this, this._onShowEffect);
        this.env.bus.on('connection_lost', this, this._onConnectionLost);
        this.env.bus.on('connection_restored', this, this._onConnectionRestored);
        this.env.bus.on('webclient-class-included', this, this.render);

        this.renderingInfo = null;
        this.rState = null;
        this.controllerComponentMap = new Map();
        this.allComponents = this.constructor.components;
    }
    //--------------------------------------------------------------------------
    // OWL Overrides
    //--------------------------------------------------------------------------
    catchError(e) {
        if (e && e.name) {
            // Real runtime error
            throw e;
        }
        // Errors that have been handled before
        console.warn(e);
        const newStack = this.renderingInfo.controllerStack;
        const newDialog = this.renderingInfo.dialog;
        this.actionManager.rollBack(newStack, newDialog);
    }
    mounted() {
        super.mounted();
        this._wcUpdated();
        odoo.isReady = true;
        this.env.bus.trigger('web-client-mounted');
    }
    patched() {
        super.patched();
        this._wcUpdated();
    }
    willPatch() {
        super.willPatch();
        const scrollPosition = this._getScrollPosition();
        this._storeScrollPosition(scrollPosition);
    }
    async willStart() {
        await this._loadMenus();
        const state = this._getUrlState();
        this._determineCompanyIds(state);
        return this._loadState(state);
    }

    get bodyClass() {
        return {
            o_fullscreen: this.renderingInfo && this.renderingInfo.fullscreen,
            o_rtl: this.env._t.database.parameters.direction === 'rtl',
            o_touch_device: this.env.device.touch,
        };
    }
    get isRendering() {
        return !!this.renderingInfo;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    _cancel() {
        if (this.isRendering) {
            this.__owl__.currentFiber.cancel();
        }
        this.renderingInfo = null;
    }
    _computeTitle() {
        const parts = Object.keys(this._titleParts).sort();
        let tmp = "";
        for (let part of parts) {
            const title = this._titleParts[part];
            if (title) {
                tmp = tmp ? tmp + " - " + title : title;
            }
        }
        return tmp;
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
    _domCleaning() {
        const body = document.body;
        // multiple bodies in tests
        const tooltips = body.querySelectorAll('body .tooltip');
        for (let tt of tooltips) {
            tt.parentNode.removeChild(tt);
        }
    }
    _getHomeAction() {
        let menuID = this.menus ? this.menus.root.children[0] : null;
        let actionID =  menuID ? this.menus[menuID].actionID : null;
        if (this.env.session.home_action_id) {
            actionID = this.env.session.home_action_id;
            menuID = null;
        }
        return { actionID , menuID };
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
            } else if (val) {
                decodedVal = decodeURI(val);
            }
            if (decodedVal) {
                state[key] = isNaN(decodedVal) ? decodedVal : parseInt(decodedVal, 10);
            }
        }

        return state;
    }
    _getWindowHash() {
        return window.location.hash;
    }
    _getWindowTitle() {
        return document.title;
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
            this._processMenu(menuData);
            odoo.loadMenusPromise = null;
        });
    }
    async _loadState(state) {
        let stateLoaded = await this.actionManager.loadState(state, { menuID: state.menu_id });
        if (stateLoaded === null) {
            if ('menu_id' in state) {
                const action = this.menus[state.menu_id].actionID;
                return this.actionManager.doAction(action, state);
            } else if (('home' in state || Object.keys(state).filter(key => key !== 'cids').length === 0)) {
                const {actionID , menuID} = this._getHomeAction();
                if (actionID) {
                    return this.actionManager.doAction(actionID, {menuID, clear_breadcrumbs: true});
                } else {
                    return true;
                }
            }
        }
        return stateLoaded;
    }
    _processMenu(menu, appID) {
        this.menus = this.menus || {};
        appID = appID || menu.id;
        const children = [];
        for (let submenu of menu.children) {
            children.push(this._processMenu(submenu, appID).id);
        }
        const action = menu.action && menu.action.split(',');
        const menuID = menu.id || 'root';
        const _menu = {
            id: menuID,
            appID: appID,
            name: menu.name,
            children: children,
            actionModel: action ? action[0] : false,
            actionID: action ? parseInt(action[1], 10) : false,
            xmlid: menu.xmlid,
        };
        this.menus[menuID] = _menu;
        return _menu;
    }
    _scrollTo(scrollPosition) {
        const scrollingEl = this.el.getElementsByClassName('o_content')[0];
        if (!scrollingEl) {
            return;
        }
        scrollingEl.scrollTop = scrollPosition.top || 0;
        scrollingEl.scrollLeft = scrollPosition.left || 0;
    }
    _setActionManager() {
        this.actionManager = new ActionManager(this.env);
        this.actionManager.on('cancel', this, this._cancel);
        this.actionManager.on('update', this, this._onActionManagerUpdated);
        this.actionManager.on('clear-uncommitted-changes', this, async (callBack) => {
            if (!this.currentDialogComponent.comp && this.currentMainComponent.comp) {
                await this.currentMainComponent.comp.canBeRemoved();
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
    _setTitlePart(part, title) {
        this._titleParts[part] = title;
    }
    _setWindowHash(newHash) {
        this.ignoreHashchange = true;
        window.location.hash = newHash;
    }
    _setWindowTitle(title) {
        document.title = title;
    }
    _storeScrollPosition(scrollPosition) {
        const cStack = this.renderingInfo.controllerStack;
        const { controller } = cStack[cStack.length-2] || {};
        if (controller) {
            controller.scrollPosition = scrollPosition;
        }
    }
    /**
     * @private
     * @param {Object} state
     */
    _updateState(state) {
        // the action and menu_id may not have changed
        state.action = state.action || this.state.action || null;
        const menuID = state.menu_id || this.state.menu_id || '';
        if (menuID) {
            state.menu_id = menuID;
        }
        if ('title' in state) {
            this._setTitlePart('action', state.title);
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
        this._setWindowTitle(this._computeTitle());
    }
    _wcUpdated() {
        if (this.renderingInfo) {
            let state = {};
            if (this.renderingInfo.main) {
                const main = this.renderingInfo.main;
                const mainComponent = this.currentMainComponent.comp;
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
            const newStack = this.renderingInfo.controllerStack || [];
            const newDialog = this.renderingInfo.dialog;
            this.actionManager.commit(newStack, newDialog, this.renderingInfo.onCommit);

            if (this.renderingInfo.menuID) {
                state.menu_id = this.renderingInfo.menuID;
            }
            if (!this.renderingInfo.dialog) {
                this._updateState(state);
            }
        }
        this.rState = this.renderingInfo;
        if (this.rState && this.rState.main) {
            this.rState.main.reload = false;
        }
        this.renderingInfo = null;
        this.env.bus.trigger('web-client-updated', this);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

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
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.detail
     */
    _onExecuteAction(ev) {
        this.actionManager.executeInFlowAction(ev.detail);
    }
    _onGenericClick(ev) {
        this._domCleaning();
        const target = ev.target;
        if (!target.tagName === 'a') {
            return;
        }
        var disable_anchor = target.attributes.disable_anchor;
        if (disable_anchor && disable_anchor.value === "true") {
            return;
        }

        var href = target.attributes.href;
        if (href) {
            if (href.value[0] === '#' && href.value.length > 1) {
                let matchingEl = null;
                try {
                    matchingEl = this.el.querySelector(`.o_content #${href.value.substr(1)}`);
                } catch (e) {} // Inavlid selector: not an anchor anyway
                if (matchingEl) {
                    ev.preventDefault();
                    const {top, left} = matchingEl.getBoundingClientRect();
                    this._scrollTo({top, left});
                }
            }
        }
    }
    async _onHashchange() {
        if (!this.ignoreHashchange) {
            const state = this._getUrlState();
            const loaded = await this._loadState(state);
            if (loaded === true) {
                this.render();
            }
        }
        this.ignoreHashchange = false;
        // TODO: reset oldURL in case of failure?
     }
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
     * @param {Object} ev.detail.state
     */
    _onPushState(ev) {
        if (!this.isRendering) {
            // Deal with that event only if we are not in a rendering cycle
            // i.e.: the rendering cycle will update the state at its end
            // Any event hapening in the meantime would be irrelevant
            this._updateState(ev.detail.state);
        }
    }
    _onSetTitlePart(ev) {
        const part = ev.detail.part;
        const title = ev.detail.title;
        this._setTitlePart(part, title);
        if (!this.isRendering) {
            this._setWindowTitle(this._computeTitle());
        }
    }
    /**
     * Displays a visual effect (for example, a rainbowMan0
     *
     * @private
     * @param {Object} payload
     * @param {Object} [ev.detail] - key-value options to decide rainbowMan
     *   behavior / appearance
     */
    _onShowEffect(payload) {
        if (this.isRendering && !payload.force) {return;}
        const type = payload.type || 'rainbow_man';
        if (type === 'rainbow_man') {
            if (this.env.session.show_effect) {
                RainbowMan.display(payload, {target: this.el, parent: this});
            } else {
                // For instance keep title blank, as we don't have title in data
                this._displayNotification({
                    title: "",
                    message: payload.message,
                    sticky: false
                });
            }
        } else {
            throw new Error('Unknown effect type: ' + type);
        }
    }
}
WebClient.components = { ActionAdapter, Menu, DialogAction, ComponentAdapter };
WebClient.template = 'web.WebClient';

return WebClient;

});
