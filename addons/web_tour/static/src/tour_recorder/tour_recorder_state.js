import { browser } from "@web/core/browser/browser";

const CURRENT_TOUR_RECORDER_LOCAL_STORAGE = "current_tour_recorder";
const CURRENT_TOUR_RECORDER_RECORD_LOCAL_STORAGE = "current_tour_recorder.record";
export const TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY = "tour_recorder_active";

/**
 * Wrapper around localStorage for persistence of the current recording.
 * Useful for resuming recording when the page refreshed.
 */
export const tourRecorderState = {
    isRecording() {
        return browser.localStorage.getItem(CURRENT_TOUR_RECORDER_RECORD_LOCAL_STORAGE) || "0";
    },
    setIsRecording(isRecording) {
        browser.localStorage.setItem(
            CURRENT_TOUR_RECORDER_RECORD_LOCAL_STORAGE,
            isRecording ? "1" : "0"
        );
    },
    setCurrentTourRecorder(tour) {
        tour = JSON.stringify(tour);
        browser.localStorage.setItem(CURRENT_TOUR_RECORDER_LOCAL_STORAGE, tour);
    },
    getCurrentTourRecorder() {
        const tour = browser.localStorage.getItem(CURRENT_TOUR_RECORDER_LOCAL_STORAGE) || "[]";
        return JSON.parse(tour);
    },
    clear() {
        browser.localStorage.removeItem(CURRENT_TOUR_RECORDER_LOCAL_STORAGE);
        browser.localStorage.removeItem(CURRENT_TOUR_RECORDER_RECORD_LOCAL_STORAGE);
    },
};
