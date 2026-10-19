/**
 * Check if a point is inside the shape
 *
 * @param {number} x - X coordinate in local space
 * @param {number} y - Y coordinate in local space
 * @param {Object} config - Shape configuration
 * @param {number} config.width - Width of the shape
 * @param {number} config.height - Height of the shape
 * @param {number} config.borderRadius - Border radius
 * @returns {boolean} True if point is inside the shape
 */
export function isPointInsideShape(x, y, config) {
    const { width, height, borderRadius } = config;

    const halfW = width / 2;
    const halfH = height / 2;

    // Clamp border radius to match CSS behavior
    const maxRadius = Math.min(halfW, halfH);
    const radius = Math.min(borderRadius, maxRadius);

    if (radius === 0) {
        // Simple rectangle
        return Math.abs(x) <= halfW && Math.abs(y) <= halfH;
    } else if (halfW === halfH && radius >= maxRadius) {
        // Perfect circle only
        const dist = Math.sqrt(x * x + y * y);
        return dist <= halfW;
    } else {
        // Rounded rectangle
        const absX = Math.abs(x);
        const absY = Math.abs(y);
        const cornerCenterX = halfW - radius;
        const cornerCenterY = halfH - radius;

        if (absX <= cornerCenterX || absY <= cornerCenterY) {
            // In the rectangular part
            return absX <= halfW && absY <= halfH;
        } else {
            // In the corner region - check distance to corner center
            const dx = absX - cornerCenterX;
            const dy = absY - cornerCenterY;
            const distToCornerCenter = Math.sqrt(dx * dx + dy * dy);
            return distToCornerCenter <= radius;
        }
    }
}

/**
 * Check if a click is on the border of a shape (border is entirely inside the shape)
 *
 * @param {number} screenX - X coordinate in screen space
 * @param {number} screenY - Y coordinate in screen space
 * @param {Object} config - Shape configuration
 * @param {number} config.x - Center X position of the shape
 * @param {number} config.y - Center Y position of the shape
 * @param {number} config.width - Width of the shape
 * @param {number} config.height - Height of the shape
 * @param {number} config.borderRadius - Border radius
 * @param {number} config.borderThickness - Border thickness
 * @param {number} config.rotation - Rotation in degrees
 * @param {number} config.scale - Scale factor
 * @param {Set<string>} config.hiddenBordersSet - Optional Set of hidden border sides ('top', 'bottom', 'left', 'right')
 * @returns {boolean} True if click is on the border (excluding hidden borders unless at corner with no radius)
 */
export function isClickOnBorder(screenX, screenY, config) {
    const { borderThickness, width, height, borderRadius, hiddenBordersSet } = config;

    const local = transformPointToLocal(screenX, screenY, config);
    const isInside = isPointInsideShape(local.x, local.y, config);

    if (!isInside) {
        return false;
    }

    // Point is inside, now check if it's in the border region
    const distToBorder = distanceToBorder(local.x, local.y, config);
    const isOnBorder = distToBorder <= borderThickness;

    if (!isOnBorder) {
        return false;
    }

    // If no hidden borders, all borders are clickable
    if (!hiddenBordersSet || hiddenBordersSet.size === 0) {
        return true;
    }

    // Determine which side(s) the click is on
    const halfW = width / 2;
    const halfH = height / 2;

    const distToTop = halfH - Math.abs(local.y);
    const distToBottom = halfH - Math.abs(local.y);
    const distToLeft = halfW - Math.abs(local.x);
    const distToRight = halfW - Math.abs(local.x);

    // Determine which edges we're closest to
    const isNearTop = local.y < 0 && distToTop <= borderThickness;
    const isNearBottom = local.y > 0 && distToBottom <= borderThickness;
    const isNearLeft = local.x < 0 && distToLeft <= borderThickness;
    const isNearRight = local.x > 0 && distToRight <= borderThickness;

    // If borderRadius > 0, don't allow clicks on hidden borders at all
    if (borderRadius > 0) {
        if (
            (isNearTop && hiddenBordersSet.has("top")) ||
            (isNearBottom && hiddenBordersSet.has("bottom")) ||
            (isNearLeft && hiddenBordersSet.has("left")) ||
            (isNearRight && hiddenBordersSet.has("right"))
        ) {
            return false;
        }
        return true;
    }

    // borderRadius === 0: Allow corners even if one border is hidden
    // Only reject if ALL touching borders are hidden

    // Check corners
    if (isNearTop && isNearLeft) {
        // Top-left corner
        return !hiddenBordersSet.has("top") || !hiddenBordersSet.has("left");
    }
    if (isNearTop && isNearRight) {
        // Top-right corner
        return !hiddenBordersSet.has("top") || !hiddenBordersSet.has("right");
    }
    if (isNearBottom && isNearLeft) {
        // Bottom-left corner
        return !hiddenBordersSet.has("bottom") || !hiddenBordersSet.has("left");
    }
    if (isNearBottom && isNearRight) {
        // Bottom-right corner
        return !hiddenBordersSet.has("bottom") || !hiddenBordersSet.has("right");
    }

    // On a single edge (not corner)
    if (isNearTop && hiddenBordersSet.has("top")) {
        return false;
    }
    if (isNearBottom && hiddenBordersSet.has("bottom")) {
        return false;
    }
    if (isNearLeft && hiddenBordersSet.has("left")) {
        return false;
    }
    if (isNearRight && hiddenBordersSet.has("right")) {
        return false;
    }

    return true;
}

/**
 * Transform a point from screen space to the element's local coordinate system
 *
 * @param {number} screenX - X coordinate in screen space
 * @param {number} screenY - Y coordinate in screen space
 * @param {Object} config - Shape configuration
 * @param {number} config.x - Center X position of the shape
 * @param {number} config.y - Center Y position of the shape
 * @param {number} config.rotation - Rotation in degrees
 * @param {number} config.scale - Scale factor
 * @returns {{x: number, y: number}} Local coordinates
 */
export function transformPointToLocal(screenX, screenY, config) {
    const { x, y, rotation, scale } = config;

    let localX = screenX - x;
    let localY = screenY - y;

    localX /= scale;
    localY /= scale;

    const angle = (-rotation * Math.PI) / 180;
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);

    const rotatedX = localX * cos - localY * sin;
    const rotatedY = localX * sin + localY * cos;

    return { x: rotatedX, y: rotatedY };
}

/**
 * Calculate distance from a point to the border of a shape
 *
 * @param {number} localX - X coordinate in local space
 * @param {number} localY - Y coordinate in local space
 * @param {Object} config - Shape configuration
 * @param {number} config.width - Width of the shape
 * @param {number} config.height - Height of the shape
 * @param {number} config.borderRadius - Border radius
 * @returns {number} Distance to the nearest border edge
 */
export function distanceToBorder(localX, localY, config) {
    const { width, height, borderRadius } = config;

    const halfW = width / 2;
    const halfH = height / 2;

    // Clamp border radius to match CSS behavior
    const maxRadius = Math.min(halfW, halfH);
    const effectiveRadius = Math.min(borderRadius, maxRadius);

    const absX = Math.abs(localX);
    const absY = Math.abs(localY);

    // No rounding - simple rectangle
    if (effectiveRadius === 0) {
        const distToVertEdge = halfW - absX;
        const distToHorizEdge = halfH - absY;
        return Math.min(distToVertEdge, distToHorizEdge);
    }

    //  Perfect circle (width === height and fully rounded)
    if (halfW === halfH && effectiveRadius >= maxRadius) {
        const dist = Math.sqrt(localX * localX + localY * localY);
        return Math.abs(dist - halfW);
    }

    // Rounded rectangle (includes stadium/pill shapes)
    // Determine which region the point is in
    const cornerCenterX = halfW - effectiveRadius;
    const cornerCenterY = halfH - effectiveRadius;

    if (absX > cornerCenterX && absY > cornerCenterY) {
        // Corner region - calculate distance to circular arc
        const dx = absX - cornerCenterX;
        const dy = absY - cornerCenterY;
        const distToCornerCenter = Math.sqrt(dx * dx + dy * dy);
        return Math.abs(distToCornerCenter - effectiveRadius);
    } else {
        // Straight edge region
        const distToVertEdge = halfW - absX;
        const distToHorizEdge = halfH - absY;
        return Math.min(distToVertEdge, distToHorizEdge);
    }
}
