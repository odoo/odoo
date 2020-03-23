odoo.define('web.ActionAdapter', function (require) {
    "use strict";

    /**
     * This file defines the Action component which is instantiated by the
     * ActionManager.
     *
     * For the sake of backward compatibility, it uses an ComponentAdapter.
     */

    const AbstractView = require('web.AbstractView');
    const { ComponentAdapter } = require('web.OwlCompatibility');

    var dom = require('web.dom');

    class ActionAdapter extends ComponentAdapter {
        constructor(parent, props) {
            super(...arguments);
            if (!(props.Component.prototype instanceof owl.Component)) {
                this.legacy = true;
                this.widgetReloadProm = null;
            }
            this.boundController = this.props.action.controller;
            this.inDialog = 'inDialog' in this.props;
        }

        //--------------------------------------------------------------------------
        // OWL Overrides
        //--------------------------------------------------------------------------

        destroy(force) {
            if (!this.inDialog && this.__owl__.isMounted && this.legacy && this.widget && !force) { // FIXME: do not detach twice?
                // keep legacy stuff alive because some stuff
                // are kept by AbstractModel (e.g.: orderedBy)
                dom.detach([{widget: this.widget}]);
                this.legacyZombie = true;
                return;
            }
            return super.destroy();
        }
        patched() {
            if (this.legacy) {
                this.widgetReloadProm = null;
                if (this.legacyZombie) {
                    if (this.widget && this.widget.on_attach_callback) {
                        this.widget.on_attach_callback();
                    }
                    this.legacyZombie = false;
                }
            }
        }
        shouldUpdate(nextProps) {
            if (this.legacy) {
                const activatingViewType = nextProps.action.controller.viewType;
                let zombie = this.legacyZombie;
                if (activatingViewType === this.widget.viewType) {
                    zombie = false;
                }
                return !zombie;
            }
            return super.shouldUpdate(nextProps);
        }
        async willStart() {
            if (this.props.Component.prototype instanceof AbstractView) {
                const action = this.props.action;
                const viewDescr = action.views.find(view => view.type === action.controller.viewType);
                const viewParams = Object.assign(
                    {},
                    { action: action, controllerState: action.controllerState },
                    action.controller.viewOptions,
                );
                const view = new viewDescr.View(viewDescr.fieldsView, viewParams);
                this.widget = await view.getController(this);
                if (this.__owl__.isDestroyed) { // the action has been destroyed meanwhile
                    this.widget.destroy();
                    return;
                }
                if (this.inDialog) {
                    this.env.bus.trigger('legacy-action', this.widget);
                }
                this.legacy = 'view';
                this._reHookControllerMethods();
                return this.widget._widgetRenderAndInsert(() => {});
            } else if (this.legacy) {
                this.legacy = 'action';
            }
            return super.willStart();
        }


        //--------------------------------------------------------------------------
        // Getters
        //--------------------------------------------------------------------------

        get title() {
            if (this.legacy && this.widget) {
                return this.widget.getTitle();
            }
            return this.props.action.name;
        }
        get widgetArgs() {
            return [this.props.action, this.props.options];
        }

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        async canBeRemoved() {
            if (this.legacy && this.widget) {
                return this.widget.canBeRemoved();
            }
        }
        /**
         * @returns {Widget | Component | null} the legacy widget or owl Component
         *   instance, or null if this function is called too soon
         */
        getController() {
            return this.widget || (this.componentRef && this.componentRef.comp) || null;
        }
        getState() {
            if (this.widget) {
                return this.widget.getState();
            }
            return {}; // TODO
        }
        exportState() {
            if (this.widget && this.widget.exportState) {
                return this.widget.exportState();
            }
            return this.getState();
        }
        async updateWidget(nextProps) {
            if (this.widgetReloadProm || ('reload' in nextProps && !nextProps.reload)) {
                return this.widgetReloadProm;
            }
            if (this.legacy === 'view') {
                const action = nextProps.action;
                const controllerState = action.controllerState || {};
                const reloadParam = Object.assign(
                    {offset: 0,},
                    action.controller.viewOptions,
                    nextProps.options,
                    {
                         controllerState
                    },
                );
                if (this.legacyZombie) {
                    await this.widget.willRestore();
                }
                return this.widget.reload(reloadParam);
            }
            return super.updateWidget(...arguments);
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _reHookControllerMethods() {
            const self = this;
            const widget = this.widget;
            const controllerReload = widget.reload;
            this.widget.reload = function() {
                self.widgetReloadProm = controllerReload.call(widget, ...arguments);
                return self.widgetReloadProm.then(() => {
                    self.widgetReloadProm = null;
                });
            };
            const controllerUpdate = widget.update;
            this.widget.update = function() {
                const updateProm = controllerUpdate.call(widget, ...arguments);
                const manualUpdate = !self.widgetReloadProm;
                if (manualUpdate) {
                    self.widgetReloadProm = updateProm;
                }
                return updateProm.then(() => {
                    if (manualUpdate) {
                        self.widgetReloadProm = null;
                    }
                });
            };
        }
        _trigger_up(ev) {
            const evType = ev.name;
            if (!this.inDialog && this.legacy === 'view' && this.widget && (evType === "switch_view" || evType === "execute_action")) {
                const controllerState = this.widget.exportState();
                this.env.bus.trigger('legacy-export-state', { controllerState });
            }
            return super._trigger_up(...arguments);
        }
    }

    return  ActionAdapter;
});
