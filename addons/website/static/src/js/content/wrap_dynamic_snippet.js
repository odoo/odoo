import { ignoreDOMMutations } from "./auto_hide_menu";

const DEFAULT_NUMBER_OF_ELEMENTS = 4;
const DEFAULT_NUMBER_OF_ELEMENTS_SM = 1;

export function rewrapDynamicSnippet(el, isSmallDevice) {
    if (ignoreDOMMutations) {
        ignoreDOMMutations(() => {
            _rewrapDynamicSnippet(el, isSmallDevice);
        });
    } else {
        _rewrapDynamicSnippet(el, isSmallDevice);
    }
}

function _rewrapDynamicSnippet(el, isSmallDevice) {
    isSmallDevice ??= isSmallQuery.matches;
    function computeChunkSize(
        dataset,
        { limitName, numberOfElementsName, numberOfElementsSmallDevicesName }
    ) {
        const limit = parseInt(dataset[limitName]);
        let numberOfElements;
        if (isSmallDevice) {
            numberOfElements =
                parseInt(dataset[numberOfElementsSmallDevicesName]) ||
                DEFAULT_NUMBER_OF_ELEMENTS_SM;
        } else {
            numberOfElements =
                parseInt(dataset[numberOfElementsName]) || DEFAULT_NUMBER_OF_ELEMENTS;
        }
        return Math.min(limit, numberOfElements);
    }

    const rows = [...el.querySelectorAll("[data-rewrap-row-limit]")];
    const cols = [...el.querySelectorAll("[data-rewrap-row-limit] [data-rewrap-col]")];
    if (cols.length) {
        const rowPerSlide =
            parseInt(el.querySelector(".carousel[data-row-per-slide]")?.dataset.rowPerSlide) || 1;
        const chunkSize =
            computeChunkSize(rows[0].dataset, {
                limitName: "rewrapRowLimit",
                numberOfElementsName: "rewrapRowNumberOfElements",
                numberOfElementsSmallDevicesName: "rewrapRowNumberOfElementsSmallDevices",
            }) * rowPerSlide;

        const colClass = `col-${Math.trunc((12 * rowPerSlide) / chunkSize)}`;
        for (const col of cols) {
            col.classList.remove(col.dataset.rewrapCol);
            col.classList.add(colClass);
            col.dataset.rewrapCol = colClass;
        }
        for (const row of rows) {
            const placeholder = document.createElement("div");
            placeholder.dataset.rewrapCol = "";
            row.querySelector("[data-rewrap-col]").before(placeholder);
        }
        const neededNumberOfRows = Math.ceil(cols.length / chunkSize);
        while (rows.length < neededNumberOfRows) {
            const lastRow = rows.at(-1);
            const newRow = lastRow.cloneNode(true);
            if (newRow.matches(".carousel-item.active")) {
                newRow.classList.remove("active");
            }
            lastRow.after(newRow);
            rows.push(newRow);
        }
        while (rows.length > neededNumberOfRows) {
            rows.pop().remove();
        }
        rows.forEach((row, index) => {
            row.querySelector("[data-rewrap-col]").parentElement.replaceChildren(
                ...cols.slice(index * chunkSize, (index + 1) * chunkSize)
            );
        });

        if (
            rows[0].matches(".carousel-item") &&
            !rows[0].parentElement.querySelector(".carousel-item.active")
        ) {
            rows[0].classList.add("active");
        }
    }
    const carouselEl = el.querySelector(".carousel");
    if (carouselEl) {
        const chunkSize = computeChunkSize(carouselEl.dataset, {
            limitName: "limit",
            numberOfElementsName: "numberOfElements",
            numberOfElementsSmallDevicesName: "numberOfElementsSmallDevices",
        });
        const moreThanOneChunk =
            chunkSize < carouselEl.querySelectorAll("[data-dynamic-carousel-item]").length;
        carouselEl.style.setProperty("--o-carousel-chunk-size", chunkSize);
        carouselEl.dataset.bsRide = moreThanOneChunk ? "carousel" : "false";
        carouselEl
            .querySelector(".s_dynamic_snippet_arrows")
            ?.classList.toggle("d-none", !moreThanOneChunk);
    }
}

function rewrapAll(isSmallDevice) {
    for (const el of document.querySelectorAll(".s_dynamic_snippet_content")) {
        rewrapDynamicSnippet(el, isSmallDevice);
    }
}

// The SM breakpoint
const isSmallQuery = window.matchMedia("(width <= 767px)");

document.addEventListener("DOMContentLoaded", async () => {
    rewrapAll(isSmallQuery.matches);
    isSmallQuery.addEventListener("change", () => rewrapAll(isSmallQuery.matches));
});
