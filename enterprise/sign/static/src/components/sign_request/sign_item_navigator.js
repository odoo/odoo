/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { offset } from "./utils";

/**
 * Starts the sign item navigator
 * @param { SignablePDFIframe } parent
 * @param { HTMLElement } target
 * @param { Object } types
 * @param { Environment } env
 */
export function startSignItemNavigator(parent, target, types, env) {
    function setTip(text) {
        navigator.style.fontFamily = "Helvetica";
        navigator.innerText = text;
    }

    const state = {
        started: false,
        isScrolling: false,
    };

    const navigator = document.createElement("div");
    navigator.classList.add("o_sign_sign_item_navigator");
    navigator.addEventListener("click", goToNextSignItem);
    target.append(navigator);

    const navLine = document.createElement("div");
    navLine.classList.add("o_sign_sign_item_navline");
    navigator.before(navLine);

    setTip(_t("Click to start"));
    navigator.focus();

    function goToNextSignItem() {
        if (!state.started) {
            state.started = true;
            parent.refreshSignItems();
            goToNextSignItem();
            return false;
        }
        const selectedElements = target.querySelectorAll(".ui-selected");
        selectedElements.forEach((selectedElement) => {
            selectedElement.classList.remove("ui-selected");
        });
        const signItemsToComplete = parent.checkSignItemsCompletion().sort((a, b) => {
            return (
                100 * (a.data.page - b.data.page) +
                10 * (a.data.posY - b.data.posY) +
                (a.data.posX - b.data.posX)
            );
        });
        if (signItemsToComplete.length > 0) {
            scrollToSignItem(signItemsToComplete[0]);
        }
    }

    /**
     * Sets the entire radio set on focus.
     * @param {Number} radio_set_id 
     */
    function highligtRadioSet(radio_set_id) {
        parent.checkSignItemsCompletion().filter((item) => item.data.radio_set_id === radio_set_id).forEach(item => {
            item.el.classList.add("ui-selected");
        });
    }

    function scrollToSignItem({ el: item, data }) {
        _scrollToSignItemPromise(item).then(() => {
            const type = types[data.type_id];
            if (type.item_type === "text" && item.querySelector("input")) {
                item.value = item.querySelector("input").value;
                item.focus = () => item.querySelector("input").focus();
            }
            // maybe store signature in data rather than in the dataset
            if (item.value === "" && !item.dataset.signature) {
                setTip(type.tip);
            }
            parent.refreshSignItems();
            if (data.type === "radio") {
                //we need to highligt the entire radio set items
                highligtRadioSet(data.radio_set_id);                
            } else {
                item.focus();
                item.classList.add("ui-selected");
            }
            if (["signature", "initial"].includes(type.item_type)) {
                if (item.dataset.hasFocus) {
                    const clickableElement = data.isSignItemEditable
                        ? item.querySelector(".o_sign_item_display")
                        : item;
                    clickableElement.click();
                } else {
                    item.dataset.hasFocus = true;
                }
            }
            state.isScrolling = false;
        });
    }

    function _scrollToSignItemPromise(item) {
        if (env.isSmall) {
            return new Promise((resolve) => {
                state.isScrolling = true;
                item.scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                    inline: "center",
                });
                resolve();
            });
        }
        state.isScrolling = true;
        const viewer = target.querySelector("#viewer");
        const containerHeight = target.offsetHeight;
        const viewerHeight = viewer.offsetHeight;

        let scrollOffset = containerHeight / 4;
        const scrollTop = offset(item).top - offset(viewer).top - scrollOffset;
        if (scrollTop + containerHeight > viewerHeight) {
            scrollOffset += scrollTop + containerHeight - viewerHeight;
        }
        if (scrollTop < 0) {
            scrollOffset += scrollTop;
        }
        scrollOffset +=
            offset(target).top -
            navigator.offsetHeight / 2 +
            item.getBoundingClientRect().height / 2;

        const duration = Math.max(
            Math.min(
                500,
                5 *
                    (Math.abs(target.scrollTop - scrollTop) +
                        Math.abs(navigator.getBoundingClientRect().top) -
                        scrollOffset)
            ),
            100
        );

        return new Promise((resolve, reject) => {
            target.scrollTo({ top: scrollTop, behavior: "smooth" });
            const an = navigator.animate(
                { top: `${scrollOffset}px` },
                { duration, fill: "forwards" }
            );
            const an2 = navLine.animate(
                { top: `${scrollOffset}px` },
                { duration, fill: "forwards" }
            );
            Promise.all([an.finished, an2.finished]).then(() => resolve());
        });
    }

    function toggle(force) {
        navigator.style.display = force ? "" : "none";
        navLine.style.display = force ? "" : "none";
    }

    return {
        setTip,
        goToNextSignItem,
        toggle,
        state,
    };
}
