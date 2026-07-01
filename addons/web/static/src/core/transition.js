import { Component, onWillUpdateProps, signal, useScope, xml } from "@odoo/owl";
import { useLayoutEffect } from "@web/owl2/utils";

// Allows to disable transitions globally, useful for testing (and maybe for
// a reduced motion setting in the future?)
export const config = {
    disabled: false,
};
/**
 * Creates a transition to be used within the current component. Usage:
 *  --- in JS:
 *  this.transition = useTransition({ name: "myClass" });
 *  --- in XML:
 *  <div t-if="transition.shouldMount" t-att-class="transition.class"/>
 *
 * @param {Object} options
 * @param {string} options.name the prefix to use for the transition classes
 * @param {boolean} [options.initialVisibility=true] whether to start the
 *  transition in the on or off state
 * @param {number} [options.immediate=false] (only relevant when initialVisibility
 *  is true) set to true to animate initially. By default, there's no animation
 *  if the element is initially visible.
 * @param {number} [options.leaveDuration] the leaveDuration of the transition
 * @param {Function} [options.onLeave] a function that will be called when the
 *  element will be removed in the next render cycle
 * @returns {{ shouldMount, class }} an object containing two fields that
 *  indicate whether an element on which the transition is applied should be
 *  mounted and the class string that should be put on it
 */
export function useTransition({
    name,
    initialVisibility = true,
    immediate = false,
    leaveDuration = 500,
    onLeave = () => {},
}) {
    const scope = useScope();

    const shouldMount = signal(initialVisibility);
    const stage = signal(initialVisibility ? "enter" : "leave");

    if (config.disabled) {
        return {
            get shouldMount() {
                return shouldMount();
            },
            set shouldMount(val) {
                shouldMount.set(val);
            },
            get className() {
                return `${name} ${name}-enter-active`;
            },
            get stage() {
                return "enter-active";
            },
        };
    }
    // We need to allow the element to be mounted in the enter state so that it
    // will get the transition when we activate the enter-active class. This
    // onNextPatch allows us to activate the class that we want the next time
    // the component is patched.
    let onNextPatch = null;
    useLayoutEffect(() => {
        if (onNextPatch) {
            onNextPatch();
            onNextPatch = null;
        }
    });

    let prevState, timer;
    const transition = {
        get shouldMount() {
            return shouldMount();
        },
        set shouldMount(newState) {
            if (newState === prevState) {
                return;
            }
            clearTimeout(timer);
            prevState = newState;
            // when true - transition from enter to enter-active
            // when false - transition from enter-active to leave, unmount after leaveDuration
            if (newState) {
                if (immediate || scope.status === 1) {
                    stage.set("enter");
                    // force a render here so that we get a patch even if the state didn't change
                    signal.trigger(stage);
                    onNextPatch = () => {
                        stage.set("enter-active");
                    };
                } else {
                    stage.set("enter-active");
                }
                shouldMount.set(true);
            } else {
                stage.set("leave");
                timer = setTimeout(() => {
                    shouldMount.set(false);
                    onLeave();
                }, leaveDuration);
            }
        },
        get className() {
            return `${name} ${name}-${stage()}`;
        },
        get stage() {
            return stage();
        },
    };
    transition.shouldMount = initialVisibility;
    return transition;
}

/**
 * A higher order component that handles a transition to be used within its
 * default slot. Generally, the useTransition hook is simpler to use, but the
 * HOC has the advantage that it can be spawned as needed during the render (eg:
 * in a t-foreach loop) without knowing at setup-time how many transitions need
 * to be created. @see useTransition
 */
export class Transition extends Component {
    static template = xml`<t t-call-slot="default" t-if="this.transition.shouldMount" className="this.transition.className"/>`;
    static props = {
        name: String,
        visible: { type: Boolean, optional: true },
        immediate: { type: Boolean, optional: true },
        leaveDuration: { type: Number, optional: true },
        onLeave: { type: Function, optional: true },
        slots: Object,
    };

    setup() {
        const { immediate, visible, leaveDuration, name, onLeave } = this.props;
        this.transition = useTransition({
            initialVisibility: visible,
            immediate,
            leaveDuration,
            name,
            onLeave,
        });
        onWillUpdateProps(({ visible = true }) => {
            this.transition.shouldMount = visible;
        });
    }
}
