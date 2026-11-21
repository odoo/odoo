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
 * Every method works on the selected company, unless another one is given.
 * The selected company is the active one, until another one is selected; it
 * is then kept until a reload, for all the color pickers. A company related to
 * what is being edited can also be used, see `useCompany`.
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
    #selectedCompanyId = signal(user.activeCompany?.id);
    #usedCompanyId = signal(undefined);

    /**
     * The companies whose favorite colors are offered: the active ones, as
     * the user works with them, and the one in use (see `useCompany`).
     */
    get companies() {
        const companies = user.activeCompanies;
        const usedCompanyId = this.#usedCompanyId();
        if (usedCompanyId && !companies.some(({ id }) => id === usedCompanyId)) {
            return [...companies, user.allowedCompanies.find(({ id }) => id === usedCompanyId)];
        }
        return companies;
    }

    /**
     * Uses the favorite colors of the given company, which is related to what
     * is being edited (e.g. the company of a website), until the returned
     * function is called: the company is then selected and offered, even if
     * it is not active. Nothing changes if the company is not allowed to the
     * user, as its colors are then unknown.
     *
     * @param {number} companyId
     * @returns {() => void} restores the previously selected company
     */
    useCompany(companyId) {
        if (!(companyId in this.#colorsByCompany())) {
            return () => {};
        }
        const previousSelectedCompanyId = this.#selectedCompanyId();
        const previousUsedCompanyId = this.#usedCompanyId();
        this.#usedCompanyId.set(companyId);
        this.#selectedCompanyId.set(companyId);
        return () => {
            this.#usedCompanyId.set(previousUsedCompanyId);
            this.#selectedCompanyId.set(previousSelectedCompanyId);
        };
    }

    /**
     * @returns {number | undefined}
     */
    get selectedCompanyId() {
        return this.#selectedCompanyId();
    }

    /**
     * @param {number} companyId
     */
    selectCompany(companyId) {
        this.#selectedCompanyId.set(companyId);
    }

    /**
     * @param {number} [companyId]
     * @returns {string[]}
     */
    getColors(companyId = this.selectedCompanyId) {
        return this.#colorsByCompany()[companyId] || [];
    }

    /**
     * Only the users allowed to edit the company can change its favorite
     * colors.
     *
     * @param {number} [companyId]
     * @returns {boolean}
     */
    canEdit(companyId = this.selectedCompanyId) {
        return companyId in this.#colorsByCompany() && user.isAdmin;
    }

    /**
     * @param {string} color
     * @param {number} [companyId]
     */
    async add(color, companyId = this.selectedCompanyId) {
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
    async remove(color, companyId = this.selectedCompanyId) {
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
