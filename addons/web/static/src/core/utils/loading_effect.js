/**
 * Gives the button a loading effect by disabling it and adding a `oi` spinner
 * icon. The existing button `oi` icons will be hidden through css.
 *
 * @param {HTMLElement} btnEl - the button to disable/load
 * @return {function} a callback function that will restore the button to its
 *         initial state
 */
export function addLoadingEffect(btnEl) {
    let loaderContainerEl;
    if (!btnEl.classList.contains("o_btn_loading")) {
        // Note that pe-none is used alongside "disabled" so that the behavior
        // is the same on links not using the "btn" class -> pointer-events
        // disabled.
        btnEl.classList.add("o_btn_loading", "disabled", "pe-none");
        btnEl.disabled = true;
        btnEl.setAttribute("aria-disabled", "true");
        loaderContainerEl = document.createElement("span");
        loaderContainerEl.classList.add("o_btn_loading_spinner");
        const loaderEl = document.createElement("span");
        loaderEl.classList.add("spinner-border", "spinner-border-sm");
        loaderContainerEl.appendChild(loaderEl);
        btnEl.prepend(loaderContainerEl);
    } else {
        btnEl.classList.add("o_btn_keep_loading");
        loaderContainerEl = btnEl.querySelector(".o_btn_loading_spinner");
    }
    return () => {
        if (btnEl.classList.contains("o_btn_keep_loading")) {
            btnEl.classList.remove("o_btn_keep_loading");
            return;
        }
        btnEl.classList.remove("o_btn_loading", "disabled", "pe-none");
        btnEl.disabled = false;
        btnEl.removeAttribute("aria-disabled");
        loaderContainerEl.remove();
    };
}
