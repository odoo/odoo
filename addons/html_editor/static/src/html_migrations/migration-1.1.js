import { parseHTML } from "@html_editor/utils/html";

/**
 *
 * @param {HTMLElement} container
 * @param {*} env
 */
export function upgrade(container, env) {
    const excalidrawContainers = container.querySelectorAll("[data-embedded='draw']");
    for (const excalidrawContainer of excalidrawContainers) {
        const source = JSON.parse(excalidrawContainer.dataset.embeddedProps).source;
        const newParagraph = parseHTML(document, `<p><a href="${source}">${source}</a></p>`);
        excalidrawContainer.replaceWith(newParagraph.firstElementChild);
    }
}
