import { browser } from "@web/core/browser/browser";

const TOUR_PLAYER_CURRENT_INDEX = "tour_player.current_index";

/**
 * Wrapper around localStorage for persistence of the current player.
 * Useful for resuming player forward when the page refreshed.
 */
export const tourPlayerState = {
    setCurrentIndex(index) {
        browser.localStorage.setItem(TOUR_PLAYER_CURRENT_INDEX, index);
    },
    getCurrentIndex() {
        return browser.localStorage.getItem(TOUR_PLAYER_CURRENT_INDEX) || 0;
    },
    clear() {
        browser.localStorage.removeItem(TOUR_PLAYER_CURRENT_INDEX);
    },
};
