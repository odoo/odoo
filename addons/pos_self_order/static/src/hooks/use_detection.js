/** @odoo-module */

import { useEffect, useState } from "@odoo/owl";

/**
 * This hook returns the target detected by the intersection observer.
 * @param {ref} root : reference to the element that is the root of the intersection observer
 * @param {Object} targets : object with references to each target
 * @param {()=>{[boolean]}} getDeps : function that returns a list with one item; this item should be true when the effect should be run and false when it should be stopped
 * @param {*} callback : function that is called when the tag is detected
 * @returns {{name:string}} : object with the name of the tag that is currently selected
 */
export function useDetection(root, targets, getDeps, callback = () => {}) {
    const detected = useState({ name: "" });
    useEffect((stop) => {
        if (stop) {
            return;
        }
        /** @type{IntersectionObserverEntry[]} */
        const allVisible = {};
        const observer = new IntersectionObserver(
            (entries) => {
                let selectedName = "";

                entries.forEach((entry) => {
                    const name = entry.target.firstChild.innerHTML;

                    if (entry.isIntersecting || entry.intersectionRatio > 0) {
                        allVisible[name] = entry.intersectionRatio;
                    } else {
                        delete allVisible[name];
                    }

                    if (Object.keys(allVisible).length > 0) {
                        selectedName = Object.entries(allVisible).sort((a, b) => {
                            return b[1] - a[1];
                        })[0][0];
                    }
                });

                if (selectedName) {
                    detected.name = selectedName;
                    callback(detected);
                }
            },
            {
                root: root.el,
                rootMargin: "-100px",
            }
        );
        Object.keys(targets).forEach((tag) => {
            observer.observe(targets[tag]?.el);
        });
        return () => {
            observer.disconnect();
        };
    }, getDeps);

    return detected;
}
