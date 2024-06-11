/** @odoo-module **/


export default {
    /**
    * Load the target section background and render it when loaded.
    *
    * This method is used to pre-load the image during the questions transitions (fade out) in order
    * to be sure the image is fully loaded when setting it as background of the next question and
    * finally display it (fade in)
    *
    * This idea is to wait until new background is loaded before changing the background
    * (to avoid flickering or loading latency)
    *
    * @param {string} imageUrl
    * @private
    */
     _preloadBackground: async function (imageUrl) {
        var resolvePreload;

        // We have to manually create a promise here because the "onload" API does not provide one.
        var preloadPromise = new Promise(function (resolve, reject) {resolvePreload = resolve;});
        var background = new Image();
        background.onload = function () {
            resolvePreload(imageUrl);
        };
        background.src = imageUrl;

        return preloadPromise;
    }
};
