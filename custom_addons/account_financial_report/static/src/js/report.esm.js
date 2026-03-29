import {useComponent, useEffect} from "@odoo/owl";

function toTitleCase(str) {
    return str
        .replaceAll(".", " ")
        .replace(
            /\w\S*/g,
            (txt) => `${txt.charAt(0).toUpperCase()}${txt.substr(1).toLowerCase()}`
        );
}

function enrich(component, targetElement, selector, isIFrame = false) {
    // eslint-disable-next-line no-undef
    let doc = window.document;
    let contentDocument = targetElement;

    // If we are in an iframe, we need to take the right document
    // both for the element and the doc
    if (isIFrame) {
        contentDocument = targetElement.contentDocument;
        doc = contentDocument;
    }

    // If there are selector, we may have multiple blocks of code to enrich
    const targets = [];
    if (selector) {
        targets.push(...contentDocument.querySelectorAll(selector));
    } else {
        targets.push(contentDocument);
    }

    // Search the elements with the selector, update them and bind an action.
    for (const currentTarget of targets) {
        const elementsToWrap = currentTarget.querySelectorAll("[res-model][domain]");
        for (const element of elementsToWrap.values()) {
            const wrapper = doc.createElement("a");
            wrapper.setAttribute("href", "#");
            wrapper.addEventListener("click", (ev) => {
                ev.preventDefault();
                component.env.services.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: element.getAttribute("res-model"),
                    domain: element.getAttribute("domain"),
                    name: toTitleCase(element.getAttribute("res-model")),
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                });
            });
            element.parentNode.insertBefore(wrapper, element);
            wrapper.appendChild(element);
        }
    }
}

export function useEnrichWithActionLinks(ref, selector = null) {
    const comp = useComponent();
    useEffect(
        (element) => {
            // If we get an iframe, we need to wait until everything is loaded
            if (element.matches("iframe")) {
                element.addEventListener("load", () =>
                    enrich(comp, element, selector, true)
                );
            } else {
                enrich(comp, element, selector);
            }
        },
        () => [ref.el]
    );
}
