import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

// What the color system is compiled into, in every color preset and area.
const CONTENT = [1, 2, 3, 4, 5]
    .map(
        (index) => `
    <section class="o_cc o_cc${index} o_colored_level">
        <h1>H1</h1><h2>H2</h2><h3>H3</h3><h6>H6</h6>
        <p>Text <span class="text-muted">muted</span> <a href="#">link</a></p>
        <a href="#" class="btn btn-primary">Primary</a>
        <a href="#" class="btn btn-secondary">Secondary</a>
        <a href="#" class="btn btn-outline-primary">Outline</a>
        <ul class="nav nav-pills"><li class="nav-item"><a class="nav-link active" href="#">Pill</a></li></ul>
    </section>`
    )
    .join("");
const EXTRA_CONTENT = `
    <section>
        <p class="bg-o-color-1">bg</p><p class="text-o-color-2">text</p>
        <p class="bg-200">gray</p><p class="text-primary">primary</p>
        <span class="text-bg-success">success</span>
        <a href="#" class="btn btn-success">Success</a>
        <input class="form-control" value="input"/>
    </section>`;
const ELEMENTS = "body, header, header *, #wrap *, footer, footer *";
const PROPERTIES = [
    "color",
    "background-color",
    "background-image",
    "border-top-color",
    "box-shadow",
    "--btn-bg",
    "--btn-color",
    "--btn-border-color",
    "--btn-hover-bg",
    "--btn-hover-color",
    "--btn-active-bg",
];

function snapshot(doc) {
    return [...doc.querySelectorAll(ELEMENTS)].map((el) => {
        const style = getComputedStyle(el);
        return PROPERTIES.map((property) => style.getPropertyValue(property).trim()).join(" | ");
    });
}

/**
 * Without any change, the colors the builder previews (see
 * `color_system_preview.js`, `theme_preview.scss`) are the compiled ones.
 */
registerWebsitePreviewTour("website_theme_preview_parity", { edition: true }, () => [
    {
        content: "The previewed colors are the compiled ones",
        trigger: ":iframe #wrap",
        run() {
            const doc = this.anchor.ownerDocument;
            this.anchor.innerHTML = CONTENT + EXTRA_CONTENT;
            const noTransition = doc.createElement("style");
            noTransition.textContent = "* { transition: none !important; }";
            doc.head.append(noTransition);
            const compiled = snapshot(doc);
            // No change: nothing pending, the colors files by type.
            const customizeWebsite = {
                getPendingValue: () => undefined,
                getColorsCustomization: (colors, { colorType }) => ({
                    url: `/website/static/src/scss/options/colors/user_${
                        colorType ? `${colorType}_` : ""
                    }color_palette.scss`,
                }),
            };
            // The builder bundle is lazy loaded: it is there in edit mode.
            const { computeColorPreviewValues } = odoo.loader.modules.get(
                "@website/builder/plugins/theme/theme_colors_option"
            );
            const values = computeColorPreviewValues(
                { document: doc, dependencies: { customizeWebsite } },
                { colors: {}, nullValue: "null" }
            );
            const rootStyle = doc.documentElement.style;
            for (const [name, value] of Object.entries(values)) {
                if (value) {
                    rootStyle.setProperty(`--o-preview-${name}`, value);
                }
            }
            const previewed = snapshot(doc);
            const elements = doc.querySelectorAll(ELEMENTS);
            const differences = compiled
                .map((value, i) => [elements[i], value, previewed[i]])
                .filter(([, value, previewedValue]) => value !== previewedValue);
            for (const [el, value, previewedValue] of differences.slice(0, 10)) {
                console.log(
                    `${el.tagName}.${el.className}\ncompiled:  ${value}\npreviewed: ${previewedValue}`
                );
            }
            if (differences.length) {
                throw new Error(`${differences.length} elements differ in the preview`);
            }
        },
    },
]);
