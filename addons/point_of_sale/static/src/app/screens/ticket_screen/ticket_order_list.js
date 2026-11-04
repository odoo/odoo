import { computed, Plugin, t, useConfig, usePlugin } from "@odoo/owl";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { ConnectionLostError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { shallowEqual } from "@web/core/utils/objects";
import { TicketOrderFilters } from "./ticket_order_filters";

/**
 * Orders shown by the ticket screen. Active orders are paginated in memory; Paid and
 * Cancelled by the server (`search_order_ids`), after the orders not synced yet.
 */
export class TicketOrderList extends Plugin {
    /** @type {import("@point_of_sale/app/services/pos_store").PosStore} */
    pos = useConfig("pos", t.object());
    state = useConfig("state", t.object());
    filters = usePlugin(TicketOrderFilters);
    notification = usePlugin(NotificationPlugin);

    localOrders = computed(() => this._getLocalOrders(this.filters.values));
    orders = computed(() => this._getDisplayedOrders());

    setup() {
        this._fetchId = 0;
        this._requestedPage = null;
        this._focusOrderId = false;
        this._pages = new Map(); // list key → { totalCount, pageIds: Map(page → ids) }
    }

    get isServerPaginated() {
        return ["SYNCED", "CANCELLED"].includes(this.state.filter);
    }
    get isLocalPage() {
        return this.isServerPaginated && this.state.pageSource === "local";
    }
    /** Back online on an offline page: the user may reload the server pages. */
    get showReloadBanner() {
        return this.isLocalPage && !this.pos.data.network.offline;
    }
    /** The page being fetched, else the page shown: two quick clicks don't ask the same page. */
    get currentPage() {
        return this._requestedPage ?? this.state.page;
    }

    // ----- Pages ----- //

    get nbrPages() {
        return Math.ceil(this.totalCount / this.state.nbrByPage);
    }
    get totalCount() {
        const localCount = this.localOrders().length;
        return this.isServerPaginated ? localCount + this.state.serverTotalCount : localCount;
    }
    /** E.g. "31-60 / 500". */
    get pageLabel() {
        const totalCount = this.totalCount;
        if (!totalCount) {
            return `0/0`;
        }
        const start = (this.state.page - 1) * this.state.nbrByPage;
        const end = start + this.orders().length;
        return `${start + 1}-${end} / ${totalCount}`;
    }
    /** The filters changed: restart on page 1. */
    async reload({ focusOrderId = false } = {}) {
        this._fetchId++; // the answers for the previous filters are ignored
        this._requestedPage = null;
        this.state.loadingPage = false;
        this._focusOrderId = focusOrderId;
        this.state.page = 1;
        this._setServerPage([], 0); // not shown under the new filters while they are fetched
        if (!this.isServerPaginated) {
            return;
        }
        if (this.pos.data.network.offline) {
            this._showLocalPage(1);
            return;
        }
        const onConnectionLost = () => this._showLocalPage(1);
        if (focusOrderId) {
            await this._fetchServerPage(1, { focusOrderId, onConnectionLost });
        } else {
            await this._showServerPage(1, { onConnectionLost });
        }
    }
    /** Same filters, another page: the current one stays until the new one is fetched. */
    async changePage(page) {
        this._focusOrderId = false; // the user left the page of the focused order
        if (!this.isServerPaginated) {
            this.state.page = page;
            return;
        }
        if (this.isLocalPage) {
            this._showLocalPage(page); // even back online: see `showReloadBanner`
            return;
        }
        await this._showServerPage(page, {
            onConnectionLost: () => this._notifyPageNotLoaded(page),
        });
    }
    /** Fetches the page again, e.g. once orders were sent to the server. */
    async refresh() {
        if (!this.isServerPaginated || this.isLocalPage) {
            return;
        }
        const page = this.currentPage;
        await this._fetchServerPage(page, {
            focusOrderId: this._focusOrderId, // the order may have moved to another page
            onConnectionLost: () => this._showLocalPage(page),
        });
    }

    /** @param {number} page the page asked, shown from memory if the user switches offline */
    _notifyPageNotLoaded(page) {
        const listKey = this._getListKey();
        const close = this.notification.add(
            _t("The page couldn't be loaded: the server can't be reached."),
            {
                type: "warning",
                buttons: [
                    {
                        name: _t("Offline mode"),
                        onClick: () => {
                            close();
                            if (this._getListKey() === listKey) {
                                this._showLocalPage(page);
                            }
                        },
                    },
                ],
            }
        );
    }
    /**
     * Shows a Paid or Cancelled page: at once if already fetched, then fetched again to stay
     * up to date (see `_fetchServerPage`). Else, the list looks busy until it is fetched.
     */
    async _showServerPage(page, { onConnectionLost }) {
        const known = this.pos.data.network.offline ? null : this._getKnownPage(page);
        if (known) {
            this._showPage("server", page, known.ids, known.totalCount);
        }
        await this._fetchServerPage(page, { shownFromMemory: Boolean(known), onConnectionLost });
    }
    /** Key of the list shown: the filters and the orders per page. */
    _getListKey() {
        return JSON.stringify([this.filters.values, this.state.nbrByPage]);
    }
    /** The page already fetched for the list shown, if its orders are still in memory. */
    _getKnownPage(page) {
        const list = this._pages.get(this._getListKey());
        const ids = list?.pageIds.get(page);
        const orders = this.pos.models["pos.order"];
        return ids?.every((id) => orders.get(id)) ? { ids, totalCount: list.totalCount } : null;
    }
    /**
     * Remembers a fetched page. If the list changed (another total, or the page itself), its
     * other pages may have shifted (e.g. an order paid on another device): they are forgotten.
     * @returns {boolean} whether the list changed (or wasn't remembered yet)
     */
    _rememberPage(listKey, page, ids, totalCount) {
        const list = this._pages.get(listKey);
        const previousIds = list?.pageIds.get(page);
        const changed =
            list?.totalCount !== totalCount ||
            Boolean(previousIds && !shallowEqual(previousIds, ids));
        if (changed) {
            this._pages.set(listKey, { totalCount, pageIds: new Map() });
        }
        this._pages.get(listKey).pageIds.set(page, ids);
        return changed;
    }
    /**
     * Fetches a Paid or Cancelled page, loading only the orders missing or outdated.
     * A page `shownFromMemory` isn't replaced, so the list doesn't move under the user,
     * except page 1 when it changed: the newest orders come on top.
     */
    async _fetchServerPage(
        page,
        { focusOrderId = false, shownFromMemory = false, onConnectionLost = () => {} }
    ) {
        const fetchId = ++this._fetchId;
        this._requestedPage = page;
        this.state.loadingPage = !shownFromMemory;
        const listKey = this._getListKey();
        const nbrByPage = this.state.nbrByPage;
        let ordersInfo, totalCount, offset;
        try {
            ({ ordersInfo, totalCount, offset } = await this.pos.data.call(
                "pos.order",
                "search_order_ids",
                [],
                {
                    config_id: this.pos.config.id,
                    domain: this.filters.toDomain(this.filters.values).toList(),
                    limit: nbrByPage,
                    offset: (page - 1) * nbrByPage,
                    focus_order_id: focusOrderId,
                    local_count: this.localOrders().length,
                }
            ));
            if (fetchId !== this._fetchId) {
                return;
            }

            const idsNotInCacheOrOutdated = ordersInfo
                .filter(([id, writeDate]) => {
                    const order = this.pos.models["pos.order"].get(id);
                    return (
                        !order || deserializeDateTime(writeDate).ts > this._getLastWriteDate(order)
                    );
                })
                .map(([id]) => id);
            if (idsNotInCacheOrOutdated.length > 0) {
                await this.pos.data.loadServerOrders([["id", "in", idsNotInCacheOrOutdated]]);
                if (fetchId !== this._fetchId) {
                    return;
                }
            }
        } catch (error) {
            if (!(error instanceof ConnectionLostError)) {
                throw error;
            }
            if (fetchId === this._fetchId) {
                onConnectionLost();
            }
            return;
        } finally {
            if (fetchId === this._fetchId) {
                this._requestedPage = null;
                this.state.loadingPage = false;
            }
        }

        const ids = ordersInfo.map(([id]) => id);
        const fetchedPage = nbrByPage ? Math.floor(offset / nbrByPage) + 1 : 1;
        const changed = this._rememberPage(listKey, fetchedPage, ids, totalCount);
        if (shownFromMemory && (!changed || fetchedPage !== 1)) {
            return;
        }
        this._showPage("server", fetchedPage, ids, totalCount);
    }
    /** Offline: the synced orders in memory, paginated like the server. */
    _showLocalPage(page) {
        this._fetchId++; // a server answer still on its way is ignored
        this._requestedPage = null;
        this.state.loadingPage = false;
        const { nbrByPage } = this.state;
        const syncedOrders = this._getLocalOrders(this.filters.values, { synced: true });
        const localCount = this.localOrders().length;
        const nbrPages = Math.ceil((localCount + syncedOrders.length) / nbrByPage);
        const shownPage = Math.min(page, Math.max(nbrPages, 1));

        const start = (shownPage - 1) * nbrByPage;
        const localOnPage = Math.min(Math.max(localCount - start, 0), nbrByPage);
        const syncedStart = Math.max(start - localCount, 0);
        const pageOrders = syncedOrders.slice(syncedStart, syncedStart + nbrByPage - localOnPage);
        this._showPage(
            "local",
            shownPage,
            pageOrders.map((order) => order.id),
            syncedOrders.length
        );
    }
    /** Shows a Paid or Cancelled page: the orders not synced yet, then the synced orders `ids`. */
    _showPage(source, page, ids, totalCount) {
        this.state.pageSource = source;
        this.state.page = page;
        this._setServerPage(ids, totalCount);
    }
    _setServerPage(ids, totalCount) {
        this.state.serverPageIds = ids;
        this.state.serverTotalCount = totalCount;
    }
    /** Same as `search_order_ids`: last change of the order, its lines or their refunds. */
    _getLastWriteDate(order) {
        const records = [
            order,
            ...order.lines,
            ...order.lines.flatMap((line) => line.refund_orderline_ids),
        ];
        return Math.max(...records.map((record) => record?.write_date?.ts || 0));
    }

    // ----- Orders ----- //

    _getDisplayedOrders() {
        const localOrders = this.localOrders();
        if (!this.isServerPaginated) {
            return localOrders.slice(
                (this.state.page - 1) * this.state.nbrByPage,
                this.state.page * this.state.nbrByPage
            );
        }
        const { page, nbrByPage } = this.state;
        const start = (page - 1) * nbrByPage;
        const localPart = localOrders.slice(start, start + nbrByPage);
        const syncedPart = this.pos.models["pos.order"].readMany(this.state.serverPageIds);
        const localOrderSet = new Set(localOrders); // a synced order with a pending change
        return [...localPart, ...syncedPart.filter((order) => !localOrderSet.has(order))];
    }
    /** Orders in memory matching the filters; on Paid and Cancelled, only the unsynced ones. */
    _getLocalOrders(values, { synced = false } = {}) {
        const serverPaginated = this.isServerPaginated;
        const searchFields = this.filters.getSearchFields();
        const orders = this.pos.models["pos.order"].filter(
            (order) =>
                (!serverPaginated || this._isOnServer(order) === synced) &&
                this.filters.matches(order, values, searchFields)
        );
        return serverPaginated ? this._sortFinishedOrders(orders) : this._sortActiveOrders(orders);
    }
    /** Whether the server has the order as it is in memory (no change waiting to be sent). */
    _isOnServer(order) {
        return order.isSynced && !(this.pos.pendingOrder.write.has(order.id) && order.isDirty());
    }
    /** Oldest expected time first, so late orders stay on top. */
    _sortActiveOrders(orders) {
        const sortKey = (order) =>
            order.preset_time?.isValid ? order.preset_time : order.date_order;
        return orders.sort((a, b) => sortKey(a) - sortKey(b) || this._comparePosReference(a, b));
    }
    /** Same keys as `search_order_ids`: most recent first, unsynced orders being the newest. */
    _sortFinishedOrders(orders) {
        const serverId = (order) => (typeof order.id === "number" ? order.id : Infinity);
        return orders.sort(
            (a, b) =>
                b.date_order - a.date_order ||
                serverId(b) - serverId(a) ||
                this._comparePosReference(b, a)
        );
    }
    _comparePosReference(a, b) {
        const nameA = parseInt(a.pos_reference?.replace(/\D/g, "")) || 0;
        const nameB = parseInt(b.pos_reference?.replace(/\D/g, "")) || 0;
        return nameA - nameB;
    }
}
