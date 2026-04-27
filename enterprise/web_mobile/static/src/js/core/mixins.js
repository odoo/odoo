/** @odoo-module **/

import { user } from "@web/core/user";
import mobile from "@web_mobile/js/services/core";
import { isIosApp } from "@web/core/browser/feature_detection";
import { url } from "@web/core/utils/urls";

const DEFAULT_AVATAR_SIZE = 128;

export const accountMethodsForMobile = {
    url,
    /**
     * Update the user's account details on the mobile app
     *
     * @returns {Promise}
     */
    async updateAccount() {
        if (!mobile.methods.updateAccount) {
            return;
        }
        const base64Avatar = await accountMethodsForMobile.fetchAvatar();
        return mobile.methods.updateAccount({
            avatar: base64Avatar.substring(base64Avatar.indexOf(',') + 1),
            name: user.name,
            username: user.login,
        });
    },
    /**
     * Fetch current user's avatar as PNG image
     *
     * @returns {Promise} resolved with the dataURL, or rejected if the file is
     *  empty or if an error occurs.
     */
    fetchAvatar() {
        const avatarUrl = accountMethodsForMobile.url('/web/image', {
            model: 'res.users',
            field: 'image_medium',
            id: user.userId,
        });
        return new Promise((resolve, reject) => {
            const canvas = document.createElement('canvas');
            canvas.width = DEFAULT_AVATAR_SIZE;
            canvas.height = DEFAULT_AVATAR_SIZE;
            const context = canvas.getContext('2d');
            const image = new Image();
            image.addEventListener('load', () => {
                context.drawImage(image, 0, 0, DEFAULT_AVATAR_SIZE, DEFAULT_AVATAR_SIZE);
                resolve(canvas.toDataURL('image/png'));
            });
            image.addEventListener('error', reject);
            image.src = avatarUrl;
        });
    },
};

/**
 * Mixin to hook into the controller record's saving method and
 * trigger the update of the user's account details on the mobile app.
 *
 * @mixin
 * @name UpdateDeviceAccountControllerMixin
 *
 */
const UpdateDeviceAccountControllerMixin = {
    /**
     * @override
     */
    async save() {
        const isSaved = await this._super(...arguments);
        if (!isSaved) {
            return false;
        }
        const updated = accountMethodsForMobile.updateAccount();
        // Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@)
        if (!isIosApp()){
            await updated;
        }
        return true;
    },
};

export async function updateAccountOnMobileDevice() {
    const updated = accountMethodsForMobile.updateAccount();
    // Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@)
    if (!isIosApp()){
        await updated;
    }
}

/**
 * Trigger the update of the user's account details on the mobile app.
 */
accountMethodsForMobile.updateAccount();

export default {
    UpdateDeviceAccountControllerMixin,
    updateAccountOnMobileDevice,
};
