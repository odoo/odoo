import { loadCSS } from "@web/core/assets";

export const GOOGLE_FONTS = {
    Aleo: "Aleo,Georgia,serif",
    Anton: "Anton,Arial,sans-serif",
    "Barlow Condensed": "Barlow Condensed,Arial,sans-serif",
    Cabin: "Cabin,Arial,sans-serif",
    Catamaran: "Catamaran,Arial,sans-serif",
    Comfortaa: "Comfortaa,Arial,sans-serif",
    "DM Sans": "DM Sans,Arial,sans-serif",
    Dosis: "Dosis,Arial,sans-serif",
    Epilogue: "Epilogue,Arial,sans-serif",
    "Fira Sans": "Fira Sans,Arial,sans-serif",
    Inter: "Inter,Arial,sans-serif",
    "Josefin Sans": "Josefin Sans,Arial,sans-serif",
    Karla: "Karla,Arial,sans-serif",
    "Lucida Sans": "Lucida Sans,Arial,sans-serif",
    Lato: "Lato,Arial,sans-serif",
    Manrope: "Manrope,Arial,sans-serif",
    Merriweather: "Merriweather,Georgia,serif",
    Montserrat: "Montserrat,Arial,sans-serif",
    Mukta: "Mukta,Arial,sans-serif",
    Mulish: "Mulish,Arial,sans-serif",
    "Noto Sans": "Noto Sans,Arial,sans-serif",
    Nunito: "Nunito,Arial,sans-serif",
    "Open Sans": "Open Sans,Arial,sans-serif",
    Oswald: "Oswald,Arial,sans-serif",
    "Palatino Linotype": "Palatino Linotype,Georgia,serif",
    "Playfair Display": "Playfair Display,Georgia,serif",
    Poppins: "Poppins,Arial,sans-serif",
    Quicksand: "Quicksand,Arial,sans-serif",
    Raleway: "Raleway,Arial,sans-serif",
    Roboto: "Roboto,Arial,sans-serif",
    Rubik: "Rubik,Arial,sans-serif",
    Signika: "Signika,Arial,sans-serif",
    "Source Sans Pro": "Source Sans Pro,Arial,sans-serif",
    "Space Mono": "Space Mono,Courier New,monospace",
    Ubuntu: "Ubuntu,Arial,sans-serif",
};

/**
 * Loads a set of Google Fonts into the given document's <head>.
 *
 * @param {Document} contentDocument - The document to inject the fonts into,
 *   typically `iframeElement.contentDocument`.
 * @returns {Promise<void>}
 */
export async function loadGoogleFonts(contentDocument) {
    try {
        const fontUrl =
            "https://fonts.googleapis.com/css2?" +
            Object.keys(GOOGLE_FONTS)
                .map((f) => `family=${encodeURIComponent(f)}`)
                .join("&") +
            "&display=swap";
        return await loadCSS(fontUrl, { targetDoc: contentDocument });
    } catch {
        // Fail silently if fonts.googleapis.com is unreachable, as these fonts are destined to be an extra option (not required)
    }
}
