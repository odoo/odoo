/** @odoo-module **/

import { registry } from "@web/core/registry";

export const tourService = {
    start() {
        /**
         * @private
         * @returns {Object} All the tours as a map
         */
        function _getAllTourMap() {
            return registry.get("tourManager").tours;
        }

        /**
         * @private
         * @returns {Object} All the active tours as a map
         */
        function _getActiveTourMap() {
            return Object.fromEntries(
                Object.entries(_getAllTourMap()).filter(
                    ([key, value]) => !registry.get("tourManager").consumed_tours.includes(key)
                )
            );
        }

        /**
         * @private
         * @returns {Array} Takes an Object (map) of tours and returns all the values
         */
        function _fromTourMapToArray(tourMap) {
            return Object.values(tourMap).sort((t1, t2) => {
                return t1.sequence - t2.sequence || (t1.name < t2.name ? -1 : 1);
            });
        }

        /**
         * @returns {Array} All the tours
         */
        function getAllTours() {
            return _fromTourMapToArray(_getAllTourMap());
        }

        /**
         * @returns {Array} All the active tours
         */
        function getActiveTours() {
            return _fromTourMapToArray(_getActiveTourMap());
        }

        /**
         * @returns {Array} The onboarding tours
         */
        function getOnboardingTours() {
            return getAllTours().filter((t) => !t.test);
        }

        /**
         * @returns {Array} The testing tours
         */
        function getTestingTours() {
            return getAllTours().filter((t) => t.test);
        }

        /**
         * @param {string} tourName
         * Run a tour
         */
        function run(tourName) {
            return registry.get("tourManager").run(tourName);
        }

        /**
         * @param {string} tourName
         * Reset a tour
         */
        function reset(tourName) {
            return registry.get("tourManager").reset(tourName);
        }

        return {
            getAllTours,
            getActiveTours,
            getOnboardingTours,
            getTestingTours,
            run,
            reset,
        };
    },
};

registry.category("services").add("tour", tourService);
