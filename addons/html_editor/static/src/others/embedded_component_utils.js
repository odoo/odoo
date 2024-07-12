import { onMounted, onPatched, useRef } from "@odoo/owl";

/**
 * Get all element children with `data-embedded-editable` attribute which are
 * descendants of the host's own embedded component and not part of another
 * embedded component descendant (an embedded component can contain others).
 * If multiple elements have the same `data-embedded-editable`, only the last
 * one is considered.
 * @param {HTMLElement} host
 * @returns {Object} editableDescendants
 */
export function getEditableDescendants(host) {
    const editableDescendants = {};
    for (const candidate of host.querySelectorAll("[data-embedded-editable]")) {
        if (candidate.closest("[data-embedded]") === host) {
            editableDescendants[candidate.dataset.embeddedEditable] = candidate;
        }
    }
    return editableDescendants;
}

/**
 * Handle the rendering of an editableDescendants:
 * It is a node owned by the editor, which will be inserted under a ref of
 * the same name as the attribute `data-embedded-editable` of that node, in the
 * component's template. This allows to use editor features inside an embedded
 * component. EditableDescendants are shared in collaboration and are saved
 * between edition sessions.
 *
 * Warning: there must be a ref in the template for every editableDescendants,
 * available at all times no matter the component state to guarantee that the
 * editor can save their values at any given time, synchronously.
 *
 * @param {HTMLElement} host for the embedded component
 */
export function useEditableDescendants(host) {
    const editableDescendants = Object.freeze(getEditableDescendants(host));
    const refs = {};
    const renders = {};
    for (const name of Object.keys(editableDescendants)) {
        refs[name] = useRef(name);
        renders[name] = () => refs[name].el.replaceChildren(editableDescendants[name]);
    }
    onMounted(() => {
        for (const render of Object.values(renders)) {
            render();
        }
    });
    onPatched(() => {
        for (const [name, render] of Object.entries(renders)) {
            // Handle partial patch
            if (!host.contains(editableDescendants[name])) {
                render();
            }
        }
    });
    return editableDescendants;
}
