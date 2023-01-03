odoo.define('web.OwlCompatibility', function (require) {
    "use strict";

    const { LegacyComponent } = require("@web/legacy/legacy_component");
    const { templates } = require("@web/core/assets");

    /**
     * This file defines the necessary tools for the transition phase where Odoo
     * legacy widgets and Owl components will coexist. There are two possible
     * scenarios:
     *  1) An Owl component has to instantiate legacy widgets
     *  2) A legacy widget has to instantiate Owl components
     */

    const {
        App,
        Component,
        onMounted,
        onWillStart,
        onWillUnmount,
        onPatched,
        onWillUpdateProps,
        onWillDestroy,
        useSubEnv,
        xml,
        status,
    } = owl;

    const widgetSymbol = odoo.widgetSymbol;
    const children = new WeakMap(); // associates legacy widgets with their Owl children

    const templateForLegacy = xml`<t/>`;
    const templateForOwl = xml`<t t-component="props.Component" t-props="childProps" />`;
    /**
     * Case 1) An Owl component has to instantiate legacy widgets
     * ----------------------------------------------------------
     *
     * The ComponentAdapter is an Owl component meant to be used as universal
     * adapter for Owl components that embed Odoo legacy widgets (or dynamically
     * both Owl components and Odoo legacy widgets), e.g.:
     *
     *                           Owl Component
     *                                 |
     *                         ComponentAdapter (Owl component)
     *                                 |
     *                       Legacy Widget(s) (or Owl component(s))
     *
     *
     * The adapter takes the component/widget class as 'Component' prop, and the
     * arguments (except first arg 'parent') to initialize it as props.
     * For instance:
     *     <ComponentAdapter Component="LegacyWidget" params="params"/>
     * will be translated to:
     *     const LegacyWidget = this.props.Component;
     *     const legacyWidget = new LegacyWidget(this, this.props.params);
     *
     * If more than one argument (in addition to 'parent') is given to initialize
     * the legacy widget, the arguments order (to initialize the sub widget) has
     * to be somehow specified. There are two alternatives. One can either (1)
     * specify the prop 'widgetArgs', corresponding to the array of arguments,
     * otherwise (2) a subclass of ComponentAdapter has to be defined. This
     * subclass must override the 'widgetArgs' getter to translate arguments
     * received as props to an array of arguments for the call to init.
     * For instance:
     *     (1) <ComponentAdapter Component="LegacyWidget" firstArg="a" secondArg="b" widgetsArgs="[a, b]"/>
     *     (2) class SpecificAdapter extends ComponentAdapter {
     *             get widgetArgs() {
     *                 return [this.props.firstArg, this.props.secondArg];
     *             }
     *         }
     *         <SpecificAdapter Component="LegacyWidget" firstArg="a" secondArg="b"/>
     *
     * If the legacy widget has to be updated when props change, one must define
     * a subclass of ComponentAdapter to override 'updateWidget' and 'renderWidget'. The
     * 'updateWidget' function takes the nextProps as argument, and should update the
     * internal state of the widget (might be async, and return a Promise).
     * However, to ensure that the DOM is updated all at once, it shouldn't do
     * a re-rendering. This is the role of function 'renderWidget', which will be
     * called just before patching the DOM, and which thus must be synchronous.
     * For instance:
     *     class SpecificAdapter extends ComponentAdapter {
     *         updateWidget(nextProps) {
     *             return this.widget.updateState(nextProps);
     *         }
     *         renderWidget() {
     *             return this.widget.render();
     *         }
     *     }
     */
    class ComponentAdapter extends LegacyComponent {
        /**
         * Creates the template on-the-fly, depending on the type of Component
         * (legacy widget or Owl component).
         *
         * @override
         */
        constructor(props) {
            if (!props.Component) {
                throw Error(`ComponentAdapter: 'Component' prop is missing.`);
            }
            let template;
            if (!(props.Component.prototype instanceof Component)) {
                template = templateForLegacy;
            } else {
                template = templateForOwl;
            }
            ComponentAdapter.template = template;
            super(...arguments);
            this.template = template;

            this.widget = null; // widget instance, if Component is a legacy widget
        }

        setup() {
            onWillUpdateProps((nextProps) => {
                if (this.widget) {
                    return this.updateWidget(nextProps);
                }
            });

            let widgetIsAttached = false;
            const insertWidget = () => {
                this.removeEl();
                if (!this.widget || !this.widget.el) {
                    return;
                }
                const node = this.__owl__.firstNode();
                node.parentNode.insertBefore(this.widget.el, node);
                this.widgetEl = this.widget.el;
                widgetIsAttached = true;
            };

            onMounted(() => {
                insertWidget();
                if (this.widget && this.widget.on_attach_callback) {
                    this.widget.on_attach_callback();
                }
            });

            onPatched(() => {
                if (widgetIsAttached) {
                    this.renderWidget();
                } else {
                    insertWidget();
                }
            });

            onWillDestroy(() => this.__destroy(this.__owl__.parent.component));

            onWillStart(this.onWillStart);
            onWillUnmount(this.onWillUnmount);
        }

        onWillStart() {
            if (!(this.props.Component.prototype instanceof Component)) {
                this.widget = new this.props.Component(this, ...this.widgetArgs);
                return this.widget._widgetRenderAndInsert(() => { });
            }
        }

        onWillUnmount() {
            this.removeEl();
            if (this.widget && this.widget.on_detach_callback) {
                this.widget.on_detach_callback();
            }
        }

        removeEl() {
            if (this.widgetEl) {
                this.widgetEl.remove();
                this.widgetEl = null;
            }
        }

        __destroy() {
            this.removeEl();
            if (this.widget) {
                this.widget.destroy();
            }
        }

        get childProps() {
            if (!this._childProps) {
                this._childProps = Object.assign({}, this.props);
                delete this._childProps.Component;
            }
            return this._childProps;
        }

        /**
         * Getter that translates the props (except 'Component') into the array
         * of arguments used to initialize the legacy widget.
         *
         * Must be overriden if at least two props (other that Component) are
         * given.
         *
         * @returns {Array}
         */
        get widgetArgs() {
            if (this.props.widgetArgs) {
                return this.props.widgetArgs;
            }
            const args = Object.keys(this.props);
            args.splice(args.indexOf('Component'), 1);
            if (args.length > 1) {
                throw new Error(`ComponentAdapter has more than 1 argument, 'widgetArgs' must be overriden.`);
            }
            return args.map(a => this.props[a]);
        }

        /**
         * Can be overriden to update the internal state of the widget when props
         * change. To ensure that the DOM is updated at once, this function should
         * not do a re-rendering (which should be done by 'render' instead).
         *
         * @param {Object} nextProps
         * @returns {Promise}
         */
        updateWidget(/*nextProps*/) {
            if (this.env.isDebug('assets')) {
                console.warn(`ComponentAdapter: Widget could not be updated, maybe override 'updateWidget' function?`);
            }
        }

        /**
         * Can be overriden to re-render the widget after an update. This
         * function will be called just before patchin the DOM, s.t. the DOM is
         * updated at once. It must be synchronous
         */
        renderWidget() {
            if (this.env.isDebug('assets')) {
                console.warn(`ComponentAdapter: Widget could not be re-rendered, maybe override 'renderWidget' function?`);
            }
        }

        /**
         * Mocks _trigger_up to redirect Odoo legacy events to OWL events.
         *
         * @private
         * @param {OdooEvent} ev
         */
        _trigger_up(ev) {
            const evType = ev.name;
            const payload = ev.data;
            if (evType === 'call_service') {
                let args = payload.args || [];
                if (payload.service === 'ajax' && payload.method === 'rpc') {
                    // ajax service uses an extra 'target' argument for rpc
                    args = args.concat(ev.target);
                }
                const service = this.env.services[payload.service];
                //If the service doesn't exist it means that it was translated to Owl
                if (service) {
                    const result = service[payload.method].apply(service, args);
                    payload.callback(result);
                } else {
                    throw new Error(
                        `The service "${payload.service}" is not present in the legacy owl environment.
                         You should probably create a mapper in @web/legacy/utils`
                    );
                }
            } else if (evType === 'get_session') {
                if (payload.callback) {
                    payload.callback(this.env.session);
                }
            } else if (evType === 'load_views') {
                const params = {
                    model: payload.modelName,
                    context: payload.context,
                    views_descr: payload.views,
                };
                this.env.dataManager
                    .load_views(params, payload.options || {})
                    .then(payload.on_success);
            } else if (evType === 'load_filters') {
                return this.env.dataManager
                    .load_filters(payload)
                    .then(payload.on_success);
            } else {
                payload.__targetWidget = ev.target;
                this.trigger(evType.replace(/_/g, '-'), payload);
            }
        }

        get el() {
            if (this.widget) {
                return this.widget.el;
            }
            return super.el;
        }
    }

    const bodyRef = { get el() { return document.body } };
    function standaloneAdapter(props = {}, ref = bodyRef) {
        const env = owl.Component.env;
        const app = new App(null, {
            templates,
            env,
            dev: env.isDebug(),
            translatableAttributes: ["data-tooltip"],
            translateFn: env._t,
        });
        if (!("Component" in props)) {
            props.Component = owl.Component;
        }
        const component = app.makeNode(ComponentAdapter, props).component;
        Object.defineProperty(component, "el", {
            get() {
                return ref.el;
            }
        });
        return component;
    }

    /**
     * Case 2) A legacy widget has to instantiate Owl components
     * ---------------------------------------------------------
     *
     * The WidgetAdapterMixin and the ComponentWrapper are meant to be used
     * together when an Odoo legacy widget needs to instantiate Owl components.
     * In this case, the widgets/components hierarchy would look like:
     *
     *             Legacy Widget + WidgetAdapterMixin
     *                          |
     *                 ComponentWrapper (Owl component)
     *                          |
     *                    Owl Component
     *
     * In this case, the parent legacy widget must use the WidgetAdapterMixin,
     * which ensures that Owl hooks (mounted, willUnmount, destroy...) are
     * properly called on the sub components. Moreover, it must instantiate a
     * ComponentWrapper, and provide it the Owl component class to use alongside
     * its props. This wrapper will ensure that the Owl component will be
     * correctly updated (with willUpdateProps) like it would be if it was embed
     * in an Owl hierarchy. Moreover, this wrapper automatically redirects all
     * events triggered by the Owl component (or its descendants) to legacy
     * custom events (trigger_up) on the parent legacy widget.

     * For example:
     *      class MyComponent extends Component {}
     *      MyComponent.template = xml`<div>Owl component with value <t t-esc="props.value"/></div>`;
     *      const MyWidget = Widget.extend(WidgetAdapterMixin, {
     *          start() {
     *              this.component = new ComponentWrapper(this, MyComponent, {value: 44});
     *              return this.component.mount(this.el);
     *          },
     *          update() {
     *              return this.component.update({value: 45});
     *          },
     *      });
     */
    const WidgetAdapterMixin = {
        /**
         * Calls on_attach_callback on each child ComponentWrapper, which will
         * call __callMounted on each sub component (recursively), to mark them
         * as mounted.
         */
        on_attach_callback() {
            for (const component of children.get(this) || []) {
                component.on_attach_callback();
            }
        },
        /**
         * Calls on_detach_callback on each child ComponentWrapper, which will
         * call __callWillUnmount to mark itself and its children as no longer
         * mounted.
         */
        on_detach_callback() {
            for (const component of children.get(this) || []) {
                component.on_detach_callback();
            }
        },
        /**
         * Destroys each sub component when the widget is destroyed. We call the
         * private __destroy function as there is no need to remove the el from
         * the DOM (will be removed alongside this widget).
         */
        destroy() {
            for (const wrapper of children.get(this) || []) {
                wrapper.destroy();
            }
            children.delete(this);
        },
    };

    //----------------------------------//
    // Low-level coordination functions //
    //----------------------------------//

    /**
     * Calls "callback" recursively on a ComponentNode's hierarchy
     *
     * @param  {ComponentNode}
     * @param  {Boolean}  childrenFirst whether to execute on the bottom-most child first
     * @param  {Function} callback
     */
    function recursiveCall(node, childrenFirst = false, callback) {
        if (!childrenFirst) {
            callback(node);
        }
        for (const child of Object.values(node.children)) {
            recursiveCall(child, childrenFirst, callback);
        }
        if (childrenFirst) {
            callback(node);
        }
    }

    /**
     * Make the node able to distinguish between
     * mounting in the DOM and mounting outside of if.
     * @param  {ComponentNode} node
     */
    function prepareForFinish(node) {
        const fiber = node.fiber;
        const complete = fiber.complete;
        fiber.complete = function () {
            // if target is not in dom
            // just trigger mounted hooks on the Proxy, not on any other node
            if (!this.target.ownerDocument.contains(this.target)) {
                this.mounted = [this];
                // We skipped a bunch of mounted calls.
                // Following calls to patched may crash because of this.
                // (e.g. useEffect dependencies set in mounted and used in patched)
            }
            complete.call(this);
        };
    }

    const nodesToRemount = new WeakMap();
    /**
     * Pushed a node into the nodesToRemount WeakMap.
     * The value is a callback that sets the node for remounting
     * @param {ComponentNode} node
     * @param {function} updateAndRender The original node's prototype's
     */
    function setToRemount(node, updateAndRender) {
        let toRemount = true;

        if (!node.isPatched) {
            node.isPatched = true;
            node.mounted.push(() => {
                toRemount = false;
            });
            node.willUpdateProps.push(() => {
                const rootMounted = node.fiber.root.mounted;
                if (toRemount && !rootMounted.includes(node.fiber)) {
                    rootMounted.push(node.fiber);
                }
            });
        }
        return () => toRemount = true;
    }
    /**
     * Make the node able to remount its children nodes correctly
     * Typically, in that case we don't call willPatch and patched hooks,
     * rather, we want to call the mounted hooks
     * @param  {ComponentNode} mainNode
     */
    function prepareForRemount(mainNode) {
        const updateAndRender = mainNode.updateAndRender;
        recursiveCall(mainNode, false, (node) => {
            if (mainNode === node) {
                return;
            }
            if (nodesToRemount.has(node)) {
                nodesToRemount.get(node)();
                return;
            } else {
                nodesToRemount.set(node, setToRemount(node, updateAndRender));
            }
        });
    }

    /**
     * Registers a wrapper instance as a child of the given parent in the
     * 'children' weakMap.
     *
     * @private
     * @param {Widget} parent
     */
    function registerWrapper(parent, wrapper) {
        let parentChildren = children.get(parent);
        if (!parentChildren) {
            parentChildren = [];
            children.set(parent, parentChildren);
        }
        parentChildren.push(wrapper);
    }

    /**
     * The component class that will be instanciated between a legacy and an OWL 2 layer.
     */
    class ProxyComponent extends LegacyComponent {
        setup() {
            for (const [hookName, cb] of Object.entries(this.props.hooks)) {
                owl[hookName](cb);
            }
            onWillUnmount(() => {
                // The current el will be change if we remount after unmounting
                this._handledEvents = new Set();
            });
            this.parentWidget = this.props.parentWidget;
            this._handledEvents = new Set();
            useSubEnv({
                [widgetSymbol]: this._addListener.bind(this)
            });
        }
        /**
         * Adds an event handler that will redirect the given Owl event to an
         * Odoo legacy event. This function is called just before the event is
         * actually triggered.
         *
         * @private
         * @param {string} evType
         */
        _addListener(evType) {
            if (this.parentWidget && !this._handledEvents.has(evType) && status(this) === "mounted") {
                this._handledEvents.add(evType);
                this.el.addEventListener(evType, ev => {
                    // as the WrappeComponent has the same root node as the
                    // actual sub Component, we have to check that the event
                    // hasn't been stopped by that component (it would naturally
                    // call stopPropagation, whereas it should actually call
                    // stopImmediatePropagation to prevent from getting here)
                    if (!ev.cancelBubble) {
                        ev.stopPropagation();
                        const detail = Object.assign({}, ev.detail, {
                            __originalComponent: ev.originalComponent,
                        });
                        this.parentWidget.trigger_up(ev.type.replace(/-/g, '_'), detail);
                    }
                });
            }
        }
    }
    ProxyComponent.template = xml`<t t-component="props.Component" t-props="props.props"/>`;

    class ComponentWrapper {
        constructor(parent, Component, props) {
            if (parent instanceof Component) {
                throw new Error("ComponentWrapper must be used with a legacy Widget as parent");
            }
            this.setParent(parent);
            const _env = props.env;
            delete props.env;
            this.props = props;

            this.Component = Component;

            const env = _env || owl.Component.env;
            const appConfig = {
                env,
                templates,
                dev: "isDebug" in env ? env.isDebug() : env.debug,
                translatableAttributes: ["data-tooltip"],
                translateFn: env._t,
            };
            const app = new App(null, appConfig);
            this.app = app;
            this.node = this._makeOwlNode();
            this.env = this.node.component.env;
            app.root = this.node;
            this.__owl__ = Object.create(this.node);
            this.componentRef = { comp: null };
            this.status = "new";
            this.setup();
        }

        _makeOwlNode() {
            const resolveRender = () => {
                if (this.renderResolve) {
                    this.renderResolve();
                }
            };

            const props = {
                props: this.props,
                hooks: {
                    onMounted: resolveRender,
                    onPatched: resolveRender,
                    onRendered: () => {
                        this.componentRef.comp = Object.values(this.node.children)[0].component;
                    },
                },
                Component: this.Component,
                parentWidget: this.parentWidget,
            };
            return this.app.makeNode(ProxyComponent, props);
        }

        setup() { }

        get el() {
            return this.node.component.el;
        }

        //------------------//
        // OWL 1 - like API //
        //------------------//

        async mount(target, options) {
            if (this.status === "mounted" || this.status === "willMount") {
                return this.render();
            } else if (this.status === "destroyed") {
                return;
            }
            if (target) {
                this.target = target;
            }
            if (options) {
                this.mountOptions = options;
            }
            const remount = this.status === "unmounted";
            if (remount) {
                prepareForRemount(this.node);
            }
            this.status = "willMount";
            const prom = this.app.mountNode(this.node, this.target, this.mountOptions);
            if (remount) {
                this.node.fiber.deep = true;
            }
            prepareForFinish(this.node);
            await prom;
            if (this.target.ownerDocument.contains(this.target)) {
                this.status = "mounted";
            }
            this.node.willStart = [];
            // remove the promise.resolve from mounted callbacks
            const mounted = this.node.mounted;
            this.node.mounted = mounted.slice(0, mounted.length - 1);
            return this;
        }

        unmount() {
            this.on_detach_callback();
            this.el.remove();
            this.node.bdom = null;
        }

        render() {
            if (this.status !== "mounted") {
                return;
            }
            if (this.renderProm) {
                this.node.render(true);
                return this.renderProm;
            }
            this.renderProm = new Promise((resolve, reject) => {
                this.renderResolve = resolve;
                this.renderReject = reject;
            }).then(() => {
                this.renderProm = null;
                this.renderResolve = null;
                this.renderReject = null;
            });
            this.node.render(true);
            return this.renderProm;
        }

        trigger() {
            return this.node.component.trigger(...arguments);
        }

        destroy() {
            if (["willMount", "unmounted"].includes(this.status)) {
                recursiveCall(this.node, false, (node) => {
                    node.willUnmount = [];
                });
            }
            this.app.destroy();
            this.status = "destroyed";
        }

        //---------------------//
        // API from legacy POV //
        //---------------------//

        get $el() {
            return $(this.el);
        }

        on_attach_callback() {
            if (!this.el || !this.el.ownerDocument.contains(this.el)) {
                return;
            }
            if (this.status === "mounted") {
                return;
            }
            recursiveCall(this.node, true, (node) => {
                for (const cb of node.mounted) {
                    cb();
                }
            });
            this.node.status = 1;
            this.status = "mounted";
        }

        /**
         * Calls willUnmount to notify the component it will be unmounted.
         */
        on_detach_callback() {
            if (this.status === "unmounted") {
                return;
            }
            recursiveCall(this.node, false, (node) => {
                // node.status might be "new" (0) here, if the component is
                // currently being re-rendered, and a new component has just
                // been instantiated, but as the rendering isn't completed, it
                // isn't mounted yet
                if (node.status === 1) {
                    const component = node.component;
                    for (const cb of node.willUnmount) {
                        cb.call(component);
                    }
                }
            });
            this.node.status = 0;
            this.status = "unmounted";
        }

        async update(nextProps) {
            if (this.status === "destroyed") {
                return;
            }
            const props = this.node.component.props.props;
            const nextComponentProps = Object.assign({}, props, nextProps);
            this.node.component.props.props = nextComponentProps;
            this.props = nextComponentProps;
            if (this.status === "unmounted") {
                return this.mount(this.target);
            } else {
                return this.render();
            }
        }

        setParent(parent) {
            if (parent instanceof Component) {
                throw new Error('ComponentWrapper must be used with a legacy Widget as parent');
            }
            if (parent) {
                registerWrapper(parent, this);
            }
            if (this.parentWidget) {
                const parentChildren = children.get(this.parentWidget);
                parentChildren.splice(parentChildren.indexOf(this), 1);
            }

            this.parentWidget = parent;
            if (this.node) {
                this.node.component.parentWidget = parent;
            }
        }
    }

    return {
        ComponentAdapter,
        ComponentWrapper,
        WidgetAdapterMixin,
        standaloneAdapter,
    };
});
