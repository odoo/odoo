odoo.define('web.OwlCompatibility', function () {
    "use strict";

    /**
     * This file defines the necessary tools for the transition phase where Odoo
     * legacy widgets and Owl components will coexist. There are two possible
     * scenarios:
     *  1) An Owl component has to instantiate legacy widgets
     *  2) A legacy widget has to instantiate Owl components
     */

    const { Component, tags } = owl;

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
     * a subclass of ComponentAdapter to override 'update' and 'render'. The
     * 'update' function takes the nextProps as argument, and should update the
     * internal state of the widget (might be async, and return a Promise).
     * However, to ensure that the DOM is updated all at once, it shouldn't do
     * a re-rendering. This is the role of function 'render', which will be
     * called just before patching the DOM, and which thus must be synchronous.
     * For instance:
     *     class SpecificAdapter extends ComponentAdapter {
     *         update(nextProps) {
     *             return this.widget.updateState(nextProps);
     *         }
     *         render() {
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
                return this.update(nextProps);
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
        __patch(vnode) {
            if (this.widget) {
                if (this.__owl__.vnode) { // not at first rendering
                    this.render();
                }
                vnode.elm = this.widget.el;
            }
            return super.__patch(...arguments);
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
        update(/*nextProps*/) {
            console.warn(`ComponentAdapter: Widget could not be updated, maybe override 'update' function?`);
        }

        /**
         * Can be overriden to re-render the widget after an update. This
         * function will be called just before patchin the DOM, s.t. the DOM is
         * updated at once. It must be synchronous
         */
        render() {
            console.warn(`ComponentAdapter: Widget could not be re-rendered, maybe override 'render' function?`);
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

    return {
        ComponentAdapter,
    };
});
