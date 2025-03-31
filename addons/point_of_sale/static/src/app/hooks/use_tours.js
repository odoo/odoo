import { tourState } from "@web_tour/tour_service/tour_state";
import { TourSelectorPopup } from "../components/tour_selector_popup/tour_selector_popup";
import { makeAwaitable } from "../store/make_awaitable_dialog";
import { useService } from "@web/core/utils/hooks";

export default function useTours() {
    const tour = useService("tour_service");
    const dialog = useService("dialog");
    const states = {
        selectedTours: new Set(),
        running: false,
        index: 0,
    };

    let fakeTourInterval = null;

    tourState.clear();

    const toggle = async () => {
        states.index = 0;
        states.running = !states.running;
        clearInterval(fakeTourInterval);

        if (!states.running) {
            tourState.clear();
            return;
        }

        const tours = await makeAwaitable(dialog, TourSelectorPopup, {});
        if (!tours || !tours.length) {
            tourState.clear();
            states.running = false;
            return;
        }

        states.selectedTours = tours;
        fakeTourInterval = setInterval(() => {
            const state = tourState.getCurrentTour();
            if (!state) {
                runTour();
            }
        }, 500);
    };

    const runTour = async () => {
        try {
            if (states.index >= states.selectedTours.length) {
                states.index = 0;
            }
            await tour.startTour(states.selectedTours[states.index], {
                stepDelay: 150,
                throw: false,
            });

            states.index++;
        } catch (error) {
            console.warn("Error in tour", error);
        }
    };

    return { toggle };
}
