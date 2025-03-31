import { browser } from "./browser/browser";

import {
    Component,
    onWillUpdateProps,
    status,
    useComponent,
    useEffect,
    useState,
    xml,
} from "@odoo/owl";

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
    const component = useComponent();
    const state = useState({
        shouldMount: initialVisibility,
        stage: initialVisibility ? "enter" : "leave",
    });

    if (config.disabled) {
        return {
            get shouldMount() {
                return state.shouldMount;
            },
            set shouldMount(val) {
                state.shouldMount = val;
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
    useEffect(() => {
        if (onNextPatch) {
            onNextPatch();
            onNextPatch = null;
        }
    });

    let prevState, timer;
    const transition = {
        get shouldMount() {
            return state.shouldMount;
        },
        set shouldMount(newState) {
            if (newState === prevState) {
                return;
            }
            browser.clearTimeout(timer);
            prevState = newState;
            // when true - transition from enter to enter-active
            // when false - transition from enter-active to leave, unmount after leaveDuration
            if (newState) {
                if (status(component) === "mounted" || immediate) {
                    state.stage = "enter";
                    // force a render here so that we get a patch even if the state didn't change
                    component.render();
                    onNextPatch = () => {
                        state.stage = "enter-active";
                    };
                } else {
                    state.stage = "enter-active";
                }
                state.shouldMount = true;
            } else {
                state.stage = "leave";
                timer = browser.setTimeout(() => {
                    state.shouldMount = false;
                    onLeave();
                }, leaveDuration);
            }
        },
        get className() {
            return `${name} ${name}-${state.stage}`;
        },
        get stage() {
            return state.stage;
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
    static template = xml`<t t-slot="default" t-if="transition.shouldMount" className="transition.className"/>`;
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
