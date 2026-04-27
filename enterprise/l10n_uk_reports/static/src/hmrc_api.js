/** @odoo-module */
export const retrieveHMRCClientInfo = () => {
    return {
        'screen_width': screen.width,
        'screen_height': screen.height,
        'screen_scaling_factor': window.devicePixelRatio,
        'screen_color_depth': screen.colorDepth,
        'window_width': window.outerWidth,
        'window_height': window.outerHeight,
    }
}
