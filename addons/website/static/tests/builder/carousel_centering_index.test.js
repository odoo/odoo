import { describe, expect, test } from "@odoo/hoot";
import { getCarouselCenteringIndex } from "@website/utils/misc";

// tests for getCarouselCenteringIndex
describe("getCarouselCenteringIndex", () => {
    test("returns null when all slides visible", () => {
        const carouselEl = document.createElement("div");
        carouselEl.className = "carousel";
        carouselEl.style.setProperty("--o-carousel-multiple-items", "5");

        for (let i = 0; i < 5; i++) {
            const item = document.createElement("div");
            item.className = "carousel-item";
            carouselEl.appendChild(item);
        }

        document.body.appendChild(carouselEl);

        const result = getCarouselCenteringIndex(carouselEl.children[2]);
        expect(result).toBe(null);

        document.body.removeChild(carouselEl);
    });

    test("centers target with odd visibleSlides", () => {
        const carouselEl = document.createElement("div");
        carouselEl.className = "carousel";
        carouselEl.style.setProperty("--o-carousel-multiple-items", "3");

        for (let i = 0; i < 10; i++) {
            const item = document.createElement("div");
            item.className = "carousel-item";
            carouselEl.appendChild(item);
        }

        document.body.appendChild(carouselEl);

        expect(getCarouselCenteringIndex(carouselEl.children[4])).toBe(3);

        document.body.removeChild(carouselEl);
    });

    test("centers target with even visibleSlides", () => {
        const carouselEl = document.createElement("div");
        carouselEl.className = "carousel";
        carouselEl.style.setProperty("--o-carousel-multiple-items", "4");

        for (let i = 0; i < 10; i++) {
            const item = document.createElement("div");
            item.className = "carousel-item";
            carouselEl.appendChild(item);
        }

        document.body.appendChild(carouselEl);

        expect(getCarouselCenteringIndex(carouselEl.children[5])).toBe(3);

        document.body.removeChild(carouselEl);
    });

    test("clamps to 0 for early items", () => {
        const carouselEl = document.createElement("div");
        carouselEl.className = "carousel";
        carouselEl.style.setProperty("--o-carousel-multiple-items", "3");

        for (let i = 0; i < 10; i++) {
            const item = document.createElement("div");
            item.className = "carousel-item";
            carouselEl.appendChild(item);
        }

        document.body.appendChild(carouselEl);

        expect(getCarouselCenteringIndex(carouselEl.children[0])).toBe(0);
        expect(getCarouselCenteringIndex(carouselEl.children[1])).toBe(0);

        document.body.removeChild(carouselEl);
    });

    test("clamps to the last 'slide' for late items", () => {
        const carouselEl = document.createElement("div");
        carouselEl.className = "carousel";
        carouselEl.style.setProperty("--o-carousel-multiple-items", "3");

        for (let i = 0; i < 10; i++) {
            const item = document.createElement("div");
            item.className = "carousel-item";
            carouselEl.appendChild(item);
        }

        document.body.appendChild(carouselEl);

        // since we have 3 visible carousel items on screen and we have 10
        // items in total, last 3 items should stay on the 7th 'slide'
        expect(getCarouselCenteringIndex(carouselEl.children[8])).toBe(7);
        expect(getCarouselCenteringIndex(carouselEl.children[9])).toBe(7);

        document.body.removeChild(carouselEl);
    });

    test("handles single visible slide", () => {
        const carouselEl = document.createElement("div");
        carouselEl.className = "carousel";
        carouselEl.style.setProperty("--o-carousel-multiple-items", "1");

        for (let i = 0; i < 5; i++) {
            const item = document.createElement("div");
            item.className = "carousel-item";
            carouselEl.appendChild(item);
        }

        document.body.appendChild(carouselEl);

        expect(getCarouselCenteringIndex(carouselEl.children[0])).toBe(0);
        expect(getCarouselCenteringIndex(carouselEl.children[2])).toBe(2);
        expect(getCarouselCenteringIndex(carouselEl.children[4])).toBe(4);

        document.body.removeChild(carouselEl);
    });
});
