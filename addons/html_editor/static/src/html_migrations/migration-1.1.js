/**
 * Remove the Excalidraw EmbeddedComponent and replace it with a link
 *
 * @param {HTMLElement} container
 * @param {Object} env
 */
export function migrate(container) {
    const excalidrawContainers = container.querySelectorAll("[data-embedded='draw']");
    for (const excalidrawContainer of excalidrawContainers) {
        const source = JSON.parse(excalidrawContainer.dataset.embeddedProps).source;
        const newParagraph = document.createElement("P");
        const anchor = document.createElement("A");
        newParagraph.append(anchor);
        anchor.append(document.createTextNode(source));
        anchor.href = source;
        excalidrawContainer.after(newParagraph);
        excalidrawContainer.remove();
    }
}
