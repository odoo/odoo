(function (exports) {
    'use strict';

    const CACHE_PRECISION = 1000;
    const FILTER_SIZE = 3;

    function lanczos(size, x) {
        if (x >= size || x <= -size) return 0;
        if (Math.abs(x) < Number.EPSILON) return 1; // x ~ 0 with floating-point precision
        const xpi = x * Math.PI;
        return size * Math.sin(xpi) * Math.sin(xpi / size) / (xpi * xpi);
    };

    function createCache(kernel, precision, filterSize) {
        const cache = {};
        const max = filterSize * filterSize * precision;
        const iprecision = 1.0 / precision;
        let value;
        // Kernel always computed on positive value
        for (let cacheKey = 0; cacheKey < max; cacheKey++) {
            value = kernel(filterSize, Math.sqrt(cacheKey * iprecision));
            cache[cacheKey] = value < 0 ? 0 : value;
        }
        return cache;
    };

    function createCanvas(width, height) {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        return canvas;
    };

    function resampleLanczos(img, width, height, options = {}) {
        const {
            filterSize = FILTER_SIZE,
            cachePrecision = CACHE_PRECISION
        } = options;
        // Store filter results in cache for performance
        const cache = createCache(lanczos, cachePrecision, filterSize);

        const inputCanvas = createCanvas(img.width, img.height);
        const inputCtx = inputCanvas.getContext("2d");
        inputCtx.drawImage(img, 0, 0);

        const src = inputCtx.getImageData(0, 0, img.width, img.height);
        const dst = inputCtx.createImageData(width, height);
        const srcData = src.data;
        const dstData = dst.data;

        const sx = width / img.width;
        const sy = height / img.height;
        const xmax = img.width - 1;
        const ymax = img.height - 1;
        const sx2 = Math.min(1, sx) ** 2;
        const sy2 = Math.min(1, sy) ** 2;
        // Precompute inverse for faster operation
        const isx = 1.0 / sx;
        const isy = 1.0 / sy;
        const iw = 1.0 / width;
        const ih = 1.0 / height;
        // Loops variables
        let a, r, g, b;
        let idx;
        let x1, x1s, x1e;
        let y1, y1s, y1e;
        let srcOffset, dstOffset;
        // Subpixel shifts
        let cx, cy;
        let centerX, centerY;
        let weight, sum, distY;

        for (let y = 0; y < height; y++) {
            centerY = (y + 0.5) * isy;
            // Clamping Y
            y1s = centerY - filterSize;
            if (y1s < 0) y1s = 0;
            y1e = centerY + filterSize;
            if (y1e > ymax) y1e = ymax;

            cy = y * ih - centerY;
            dstOffset = y * width;
            for (let x = 0; x < width; x++) {
                centerX = (x + 0.5) * isx;
                // Clamping X
                x1s = centerX - filterSize;
                if (x1s < 0) x1s = 0;
                x1e = centerX + filterSize;
                if (x1e > xmax) x1e = xmax;

                cx = x * iw - centerX;
                sum = a = r = g = b = 0;
                for (y1 = y1s >> 0; y1 <= y1e; y1++) {
                    srcOffset = y1 * img.width;
                    distY = (y1 + cy) * (y1 + cy) * sy2;
                    for (x1 = x1s >> 0; x1 <= x1e; x1++) {
                        // Weight computation with cache
                        weight = cache[((x1 + cx) * (x1 + cx) * sx2 + distY) * cachePrecision >> 0] || 0;
                        sum += weight;
                        // Color accumulation
                        idx = (srcOffset + x1) << 2;
                        r += srcData[idx] * weight;
                        g += srcData[idx + 1] * weight;
                        b += srcData[idx + 2] * weight;
                        a += srcData[idx + 3] * weight;
                    }
                }
                sum = sum > 0 ? 1.0 / sum : 0.0;
                idx = (dstOffset + x) << 2;
                dstData[idx] = r * sum;
                dstData[idx + 1] = g * sum;
                dstData[idx + 2] = b * sum;
                dstData[idx + 3] = a * sum;
            }
        }
        const outputCanvas = createCanvas(dst.width, dst.height);
        const outputCtx = outputCanvas.getContext("2d");
        outputCtx.putImageData(dst, 0, 0)
        return outputCanvas;
    }

    function resizeLanczos(img, newWidth, newHeight, options = {}) {
        // Avoid decimal sizes
        const newW = Math.floor(newWidth);
        const newH = Math.floor(newHeight);
        const canvas = resampleLanczos(img, newW, newH, options);
        return canvas;
    }

    function resizeCanvas(image, newWidth, newHeight) {
        const canvas = createCanvas(newWidth, newHeight);
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "transparent";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(
            image,
            0, 0, image.width, image.height,
            0, 0, canvas.width, canvas.height
        );
        return canvas;
    }

    function resizeImageWithResampling(image, newSize, originalSize, options = {}) {
        const ratio = newSize / originalSize;
        const newWidth = image.width * ratio;
        const newHeight = image.height * ratio;
        // Keep it thumbnails only for now to avoid performance issues
        if (newSize < originalSize && newSize < 1920) {
            try {
                return resizeLanczos(image, newWidth, newHeight, options);
            } catch (error) {
                console.warn("Lanczos resizing failed, falling back to canvas resizing:", error);
            }
        }
        return resizeCanvas(image, newWidth, newHeight);
    }

    exports.resizeImageWithResampling = resizeImageWithResampling;

})(this.lanczos = this.lanczos || {});
