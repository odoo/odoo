//-----------------------------------------------------------------------------
// ! PRODUCTION CODE: DO NOT TOUCH
//-----------------------------------------------------------------------------

/**
 * @todo should we use "click" instead of "pointerdown"?
 * @returns {HTMLButtonElement}
 */
export function createCounter() {
    const button = html`<button>${0}</button>`;
    button.addEventListener("pointerdown", () => {
        button.textContent = Number(button.textContent) + 1;
    });
    return button;
}

/**
 * @todo maybe checkboxes shouldn't be randomly checked?
 * @param {number} [amount=1]
 * @returns {HTMLDivElement}
 */
export function createRandomizedCheckboxList(amount = 1) {
    return html`<div>
        ${[...Array(amount)]
            .map(() => `<input type="checkbox" ${Math.random() < 0.5 ? "checked" : ""}>`)
            .join("")}
    </div>`;
}

/**
 * @returns {HTMLInputElement}
 */
export function createText() {
    return html`<input type="text" />`;
}

export function html() {
    const parent = document.createElement("div");
    parent.innerHTML = String.raw(...arguments);
    return parent.children[0];
}
