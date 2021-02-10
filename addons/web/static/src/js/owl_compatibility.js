odoo.define('web.OwlCompatibility', function () {
    "use strict";

    /**
     * This file defines the necessary tools for the transition phase where Odoo
     * legacy widgets and Owl components will coexist. There are two possible
     * scenarios:
     *  1) An Owl component has to instantiate legacy widgets
     *  2) A legacy widget has to instantiate Owl components
     */

    const { Component, hooks, tags } = owl;
    const { useRef, useSubEnv } = hooks;
    const { xml } = tags;

    const widgetSymbol = odoo.widgetSymbol;
    const children = new WeakMap(); // associates legacy widgets with their Owl children

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
    class ComponentAdapter extends Component {
        /**
         * Creates the template on-the-fly, depending on the type of Component
         * (legacy widget or Owl component).
         *
         * @override
         */
        constructor(parent, props) {
            if (!props.Component) {
                throw Error(`ComponentAdapter: 'Component' prop is missing.`);
            }
            let template;
            if (!(props.Component.prototype instanceof Component)) {
                template = tags.xml`<div/>`;
            } else {
                let propsStr = '';
                for (let p in props) {
                    if (p !== 'Component') {
                        propsStr += ` ${p}="props.${p}"`;
                    }
                }
                template = tags.xml`<t t-component="props.Component"${propsStr}/>`;
            }
            ComponentAdapter.template = template;
            super(...arguments);
            this.template = template;
            ComponentAdapter.template = null;

            this.widget = null; // widget instance, if Component is a legacy widget
        }

        /**
         * Starts the legacy widget (not in the DOM yet)
         *
         * @override
         */
        willStart() {
            if (!(this.props.Component.prototype instanceof Component)) {
                this.widget = new this.props.Component(this, ...this.widgetArgs);
                return this.widget._widgetRenderAndInsert(() => {});
            }
        }

        /**
         * Updates the internal state of the legacy widget (but doesn't re-render
         * it yet).
         *
         * @override
         */
        willUpdateProps(nextProps) {
            if (this.widget) {
                return this.updateWidget(nextProps);
            }
        }

        /**
         * Hooks just before the actual patch to replace the fake div in the
         * vnode by the actual node of the legacy widget. If the widget has to
         * be re-render (because it has previously been updated), re-render it.
         * This must be synchronous.
         *
         * @override
         */
        __patch(target, vnode) {
            if (this.widget) {
                if (this.__owl__.vnode) { // not at first rendering
                    this.renderWidget();
                }
                vnode.elm = this.widget.el;
            }
            const result = super.__patch(...arguments);
            if (this.widget && this.el !== this.widget.el) {
                this.__owl__.vnode.elm = this.widget.el;
            }
            return result;
        }

        /**
         * @override
         */
        mounted() {
            if (this.widget && this.widget.on_attach_callback) {
                this.widget.on_attach_callback();
            }
        }

        /**
         * @override
         */
        willUnmount() {
            if (this.widget && this.widget.on_detach_callback) {
                this.widget.on_detach_callback();
            }
        }

        /**
         * @override
         */
        __destroy() {
            super.__destroy(...arguments);
            if (this.widget) {
                this.widget.destroy();
            }
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
                const result = service[payload.method].apply(service, args);
                payload.callback(result);
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
            for (const component of children.get(this) || []) {
                component.__destroy();
            }
            children.delete(this);
        },
    };
    class ComponentWrapper extends Component {
        /**
         * Stores the reference of the instance in the parent (in __components).
         * Also creates a sub environment with a function that will be called
         * just before events are triggered (see component_extension.js). This
         * allows to add DOM event listeners on-the-fly, to redirect those Owl
         * custom (yet DOM) events to legacy custom events (trigger_up).
         *
         * @override
         * @param {Widget|null} parent
         * @param {Component} Component this is a Class, not an instance
         * @param {Object} props
         */
        constructor(parent, Component, props) {
            if (parent instanceof Component) {
                throw new Error('ComponentWrapper must be used with a legacy Widget as parent');
            }
            super(null, props);
            if (parent) {
                this._register(parent);
            }
            useSubEnv({
                [widgetSymbol]: this._addListener.bind(this)
            });

            this.parentWidget = parent;
            this.Component = Component;
            this.props = props || {};
            this._handledEvents = new Set(); // Owl events we are redirecting

            this.componentRef = useRef("component");
        }

        /**
         * Calls __callMounted on itself and on each sub component (as this
         * function isn't recursive) when the component is appended into the DOM.
         */
        on_attach_callback() {
            function recursiveCallMounted(component) {
                for (const key in component.__owl__.children) {
                    recursiveCallMounted(component.__owl__.children[key]);
                }
                component.__callMounted();
            }
            recursiveCallMounted(this);
        }
        /**
         * Calls __callWillUnmount to notify the component it will be unmounted.
         */
        on_detach_callback() {
            this.__callWillUnmount();
        }

        /**
         * Overrides to remove the reference to this component in the parent.
         *
         * @override
         */
        destroy() {
            if (this.parentWidget) {
                const parentChildren = children.get(this.parentWidget);
                if (parentChildren) {
                    const index = parentChildren.indexOf(this);
                    children.get(this.parentWidget).splice(index, 1);
                }
            }
            super.destroy();
        }

        /**
         * Changes the parent of the wrapper component. This is a function of the
         * legacy widgets (ParentedMixin), so we have to handle it someway.
         * It simply removes the reference of this component in the current
         * parent (if there was one), and adds the reference to the new one.
         *
         * We have at least one usecase for this: in views, the renderer is
         * instantiated without parent, then a controller is instantiated with
         * the renderer as argument, and finally, setParent is called to set the
         * controller as parent of the renderer. This implies that Owl renderers
         * can't trigger events in their constructor.
         *
         * @param {Widget} parent
         */
        setParent(parent) {
            if (parent instanceof Component) {
                throw new Error('ComponentWrapper must be used with a legacy Widget as parent');
            }
            this._register(parent);
            if (this.parentWidget) {
                const parentChildren = children.get(this.parentWidget);
                parentChildren.splice(parentChildren.indexOf(this), 1);
            }
            this.parentWidget = parent;
        }

        /**
         * Updates the props and re-render the component.
         *
         * @async
         * @param {Object} props
         * @return {Promise}
         */
        async update(props = {}) {
            if (this.__owl__.status === 5 /* destroyed */) {
                return new Promise(() => {});
            }

            Object.assign(this.props, props);

            let prom;
            if (this.__owl__.status === 3 /* mounted */) {
                prom = this.render();
            } else {
                // we may not be in the DOM, but actually want to be redrawn
                // (e.g. we were detached from the DOM, and now we're going to
                // be re-attached, but we need to be reloaded first). In this
                // case, we have to call 'mount' as Owl would skip the rendering
                // if we simply call render.
                prom = this.mount(...this._mountArgs);
            }
            return prom;
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
            if (this.parentWidget && !this._handledEvents.has(evType)) {
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

        /**
         * Registers this instance as a child of the given parent in the
         * 'children' weakMap.
         *
         * @private
         * @param {Widget} parent
         */
        _register(parent) {
            let parentChildren = children.get(parent);
            if (!parentChildren) {
                parentChildren = [];
                children.set(parent, parentChildren);
            }
            parentChildren.push(this);
        }
        /**
         * Stores mount target and position at first mount. That way, when updating
         * while out of DOM, we know where and how to remount.
         * @see update()
         * @override
         */
        async mount(target, options) {
            if (options && options.position === 'self') {
                throw new Error(
                    'Unsupported position: "self" is not allowed for wrapper components. ' +
                    'Contact the JS Framework team or open an issue if your use case is relevant.'
                );
            }
            this._mountArgs = arguments;
            return super.mount(...arguments);
        }
    }
    ComponentWrapper.template = xml`<t t-component="Component" t-props="props" t-ref="component"/>`;

    return {
        ComponentAdapter,
        ComponentWrapper,
        WidgetAdapterMixin,
    };
});
