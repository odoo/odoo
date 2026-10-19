export const STATIC_IMG_BASE_URL = "/pos_restaurant/static/floor_plan";

export function getEventCoords(e) {
    if (e.touches && e.touches.length > 0) {
        return { clientX: e.touches[0].clientX, clientY: e.touches[0].clientY };
    }
    return { clientX: e.clientX, clientY: e.clientY };
}

export function setElementTransform(el, left = 0, top = 0, rotation = 0, scale = 1) {
    const translateX = left;
    const translateY = top;

    if (scale !== 1) {
        el.style.transform = `translate(${translateX}px,${translateY}px) rotate(${
            rotation || 0
        }deg) scale(${scale})`;
    } else {
        el.style.transform = `translate(${translateX}px,${translateY}px) rotate(${
            rotation || 0
        }deg)`;
    }
}

export function toRad(deg) {
    return (deg * Math.PI) / 180;
}
export function toDeg(rad) {
    return (rad * 180) / Math.PI;
}
export function normDeg(deg = 0) {
    return ((deg % 360) + 360) % 360;
}

export function removeNullishAndDefault(object, defaults = {}) {
    const result = {};
    for (const key in object) {
        const value = object[key];
        if (value !== null && value !== undefined && defaults[key] !== value) {
            result[key] = value;
        }
    }
    return result;
}

// Converts transparency (0 = opaque, 100 = fully transparent)
// to opacity (0 = transparent, 1 = opaque)
export function transparencyToOpacity(transparency = 0) {
    const t = Number(transparency);
    const clamped = Math.min(100, Math.max(0, t));
    return (100 - clamped) / 100;
}

// Converts opacity (0 = transparent, 1 = opaque)
// to transparency (0 = opaque, 100 = fully transparent)
export function opacityToTransparency(opacity = 1) {
    const o = Number(opacity);
    const clamped = Math.min(1, Math.max(0, o));
    return Math.round((1 - clamped) * 100);
}

export async function convertObjectUrlToDataUrl(objectUrl) {
    const response = await fetch(objectUrl);
    const blob = await response.blob();
    return await blobToDataUrl(blob);
}

export async function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

export function loadImage(url) {
    return new Promise((resolve, reject) => {
        const img = new Image();

        img.onload = function () {
            const width = img.width;
            const height = img.height;
            resolve({ width, height, url });
        };

        img.onerror = function () {
            resolve(null);
        };

        img.src = url;
    });
}

export function applyDefaults(target, defaults) {
    for (const key in defaults) {
        if (target[key] == null) {
            // catches null AND undefined
            target[key] = defaults[key];
        }
    }
    return target;
}
