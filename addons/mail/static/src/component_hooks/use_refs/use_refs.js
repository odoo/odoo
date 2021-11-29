/** @odoo-module **/

const { Component } = owl;
const { onMounted, onWillUpdateProps, onWillUnmount, useComponent } = owl.hooks;

/**
 * This hook provides support for dynamic-refs on child components.
 * Components have reference in `this.refs`.
 * Child components must also make use of `useRefs`.
 * This component should pass `refs` and a ref name in `ref`, both as props
 * to the subcomponent.
 *
 * Example: <Child refs="refs" ref="'child'">
 *
 * This child component can be read with `this.refs.child`.
 */
export function useRefs() {
    const component = useComponent();
    component.refs = {};
    onMounted(() => {
        if (component.props.refs && component.props.ref) {
            component.props.refs[component.props.ref] = component;
        }
    });
    onWillUpdateProps(nextProps => {
        if (component.props.refs && component.props.ref) {
            delete component.props.refs[component.props.ref]
        }
        if (nextProps.refs && nextProps.ref) {
            nextProps.refs[nextProps.ref] = component;
        }
    });
    onWillUnmount(() => {
        if (component.props.refs && component.props.ref) {
            delete component.props.refs[component.props.ref]
        }
    });
}

export const useRefsProps = {
    ref: {
        type: String,
        optional: true,
    },
    refs: {
        type: Object,
        optional: true,
    },
}
