import { Plugin, signal, usePlugin } from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";
import { services } from "@web/core/services";
import { user } from "@web/core/user";

/**
 * Holds the favorite colors of the companies allowed to the user, shared by
 * all the color pickers. They are initialized from the session, then kept up
 * to date by the changes of the current user (the changes of other users only
 * show up after a reload, or along with a change of the current user).
 *
 * Every method works on the company in use, unless another one is given: the
 * active company, unless another one related to what is being edited is used
 * (see `useCompany`).
 */
export class FavoriteColorsPlugin extends Plugin {
    #orm = usePlugin(ORM);
    #colorsByCompany = signal.Object(
        Object.fromEntries(
            user.allowedCompanies.map((company) => [
                company.id,
                [...(company.favorite_colors || [])],
            ])
        )
    );
    #usedCompanyId = signal(undefined);

    /**
     * @returns {number | undefined} id of the company in use
     */
    get companyId() {
        return this.#usedCompanyId() ?? user.activeCompany?.id;
    }

    /**
     * Uses the favorite colors of the given company, which is related to what
     * is being edited (e.g. the company of a website), until the returned
     * function is called. Nothing changes if the company is not allowed to the
     * user, as its colors are then unknown.
     *
     * @param {number} companyId
     * @returns {() => void} restores the company used before
     */
    useCompany(companyId) {
        if (!(companyId in this.#colorsByCompany())) {
            return () => {};
        }
        const previousCompanyId = this.#usedCompanyId();
        this.#usedCompanyId.set(companyId);
        return () => this.#usedCompanyId.set(previousCompanyId);
    }

    /**
     * @param {number} [companyId]
     * @returns {string[]}
     */
    getColors(companyId = this.companyId) {
        return this.#colorsByCompany()[companyId] || [];
    }

    /**
     * Only the users allowed to edit the company can change its favorite
     * colors.
     *
     * @param {number} [companyId]
     * @returns {boolean}
     */
    canEdit(companyId = this.companyId) {
        return companyId in this.#colorsByCompany() && user.isAdmin;
    }

    /**
     * @param {string} color
     * @param {number} [companyId]
     */
    async add(color, companyId = this.companyId) {
        color = color.toUpperCase();
        const colors = this.getColors(companyId);
        if (!colors.includes(color)) {
            await this.#update("add_favorite_color", companyId, color, [...colors, color]);
        }
    }

    /**
     * @param {string} color
     * @param {number} [companyId]
     */
    async remove(color, companyId = this.companyId) {
        const colors = this.getColors(companyId);
        if (colors.includes(color)) {
            const newColors = colors.filter((c) => c !== color);
            await this.#update("remove_favorite_color", companyId, color, newColors);
        }
    }

    /**
     * Updates the favorite colors right away, then with the ones returned by
     * the server (which include the changes of the other users).
     *
     * Dedicated methods are called rather than `write`, as the web client
     * reloads after any `write` on a company (see `ReloadCompanyPlugin`).
     *
     * @param {"add_favorite_color" | "remove_favorite_color"} method
     * @param {number} companyId
     * @param {string} color
     * @param {string[]} colors expected favorite colors
     */
    async #update(method, companyId, color, colors) {
        const colorsByCompany = this.#colorsByCompany();
        const previousColors = [...this.getColors(companyId)];
        colorsByCompany[companyId] = colors;
        try {
            colorsByCompany[companyId] = await this.#orm.call("res.company", method, [
                [companyId],
                color,
            ]);
        } catch (error) {
            colorsByCompany[companyId] = previousColors;
            throw error;
        }
    }
}

services.add(FavoriteColorsPlugin);
