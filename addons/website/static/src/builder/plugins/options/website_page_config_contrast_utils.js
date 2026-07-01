import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { loadImage } from "@html_editor/utils/image_processing";

export const WHITE_RGB = { red: 255, green: 255, blue: 255 };

function parseLength(value, reference) {
    if (!value || value === "auto") {
        return null;
    }
    if (value.endsWith("%")) {
        return (parseFloat(value) / 100) * reference;
    }
    return parseFloat(value);
}

function parsePosition(value, reference, renderedSize, start, center, end) {
    if (value === start) {
        return 0;
    }
    if (value === center) {
        return (reference - renderedSize) / 2;
    }
    if (value === end) {
        return reference - renderedSize;
    }
    if (value?.endsWith("%")) {
        return ((reference - renderedSize) * parseFloat(value)) / 100;
    }
    return parseFloat(value) || 0;
}

function getRenderedBackgroundImageSize(style, sectionRect, image) {
    const [sizeX, sizeY] = style.backgroundSize.split(",")[0].trim().split(/\s+/);
    if (sizeX === "cover" || sizeX === "contain") {
        const widthRatio = sectionRect.width / image.naturalWidth;
        const heightRatio = sectionRect.height / image.naturalHeight;
        const ratio =
            sizeX === "cover"
                ? Math.max(widthRatio, heightRatio)
                : Math.min(widthRatio, heightRatio);
        return {
            width: image.naturalWidth * ratio,
            height: image.naturalHeight * ratio,
        };
    }

    let width = parseLength(sizeX, sectionRect.width);
    let height = parseLength(sizeY, sectionRect.height);
    if (!width && !height) {
        width = image.naturalWidth;
        height = image.naturalHeight;
    } else if (!width) {
        width = (height * image.naturalWidth) / image.naturalHeight;
    } else if (!height) {
        height = (width * image.naturalHeight) / image.naturalWidth;
    }
    return { width, height };
}

function getBackgroundImageSourceArea(style, sectionRect, sampleHeight, renderedSize, image) {
    const [positionX = "50%", positionY = "50%"] = style.backgroundPosition
        .split(",")[0]
        .trim()
        .split(/\s+/);
    const offsetX = parsePosition(
        positionX,
        sectionRect.width,
        renderedSize.width,
        "left",
        "center",
        "right"
    );
    const offsetY = parsePosition(
        positionY,
        sectionRect.height,
        renderedSize.height,
        "top",
        "center",
        "bottom"
    );
    const imageLeft = Math.max(0, -offsetX);
    const imageTop = Math.max(0, -offsetY);
    const imageRight = Math.min(renderedSize.width, sectionRect.width - offsetX);
    const imageBottom = Math.min(renderedSize.height, sampleHeight - offsetY);
    if (imageLeft >= imageRight || imageTop >= imageBottom) {
        return null;
    }
    return {
        x: (imageLeft / renderedSize.width) * image.naturalWidth,
        y: (imageTop / renderedSize.height) * image.naturalHeight,
        width: ((imageRight - imageLeft) / renderedSize.width) * image.naturalWidth,
        height: ((imageBottom - imageTop) / renderedSize.height) * image.naturalHeight,
    };
}

function blendOnWhite([red, green, blue, alpha]) {
    if (!alpha) {
        return null;
    }
    const opacity = alpha / 255;
    return {
        red: Math.round(red * opacity + 255 * (1 - opacity)),
        green: Math.round(green * opacity + 255 * (1 - opacity)),
        blue: Math.round(blue * opacity + 255 * (1 - opacity)),
    };
}

export async function getAverageBackgroundImageColor(sectionEl, sampleEl) {
    const src = getBgImageURLFromEl(sectionEl);
    if (!src) {
        return null;
    }
    const image = await loadImage(src).catch(() => null);
    if (!image?.naturalWidth || !image?.naturalHeight) {
        return null;
    }

    const document = sectionEl.ownerDocument;
    const sectionRect = sectionEl.getBoundingClientRect();
    const sampleRect = sampleEl?.getBoundingClientRect();
    const sampleHeight = Math.min(sectionRect.height, sampleRect?.height || sectionRect.height);
    const style = document.defaultView.getComputedStyle(sectionEl);
    const renderedSize = getRenderedBackgroundImageSize(style, sectionRect, image);
    const sourceArea = getBackgroundImageSourceArea(
        style,
        sectionRect,
        sampleHeight,
        renderedSize,
        image
    );
    if (!sourceArea) {
        return null;
    }

    const canvas = document.createElement("canvas");
    canvas.width = 1;
    canvas.height = 1;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) {
        return null;
    }
    try {
        context.drawImage(
            image,
            sourceArea.x,
            sourceArea.y,
            sourceArea.width,
            sourceArea.height,
            0,
            0,
            1,
            1
        );
        return blendOnWhite(context.getImageData(0, 0, 1, 1).data);
    } catch {
        return null;
    }
}
