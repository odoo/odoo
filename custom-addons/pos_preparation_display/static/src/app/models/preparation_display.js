/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";
import { Order } from "@pos_preparation_display/app/models/order";
import { Orderline } from "@pos_preparation_display/app/models/orderline";
import { Stage } from "@pos_preparation_display/app/models/stage";
import { Category } from "@pos_preparation_display/app/models/category";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { Product } from "@pos_preparation_display/app/models/product";
import { ConnectionLostError } from "@web/core/network/rpc_service";

// in the furur, maybe just set "filterOrders" as a getter and directly call the function.
export class PreparationDisplay extends Reactive {
    constructor({ categories, orders, stages }, env, preparationDisplayId) {
        super();
        this.ready = this.setup(...arguments).then(() => this);
    }
    async setup(data, env, preparationDisplayId) {
        this.id = preparationDisplayId;
        this.env = env;
        this.showCategoryFilter = false;
        this.orm = env.services.orm;
        this.orders = {};
        this.orderlines = {};
        this.categories = {};
        this.products = {};
        this.stages = new Map(); // We need a Map() and not an object because the order of the elements is important
        this.selectedStageId = 0;
        this.selectedCategories = new Set();
        this.selectedProducts = new Set();
        this.filteredOrders = [];
        this.noteByLines = {};
        this.rawData = {
            categories: data.categories,
            orders: data.orders,
            stages: data.stages,
            attributes: data.attributes,
            attributeValues: data.attribute_values,
        };

        this.restoreFilterFromLocalStorage();
        this.processStages();
        this.processCategories();
        this.processOrders();
        this.attributes = data.attributes;
        this.attributeValues = data.attribute_values;
        this.posHasProducts = await this.loadPosHasProducts();
        this.loadingProducts = false;
    }

    filterOrders() {
        const stages = this.stages;
        const countedOrders = new Set();
        let ordersToDisplay = [];

        this.stages.forEach((stage) => (stage.orderCount = 0));
        ordersToDisplay = Object.values(this.orders)
            .filter((order) => {
                return order.orderlines.find((orderline) => {
                    // the order must be in selected categories or products (if set) and must be flag as displayed.
                    if (!this.checkOrderlineVisibility(orderline) || !order.displayed) {
                        return;
                    }
                    if (!countedOrders.has(order.id)) {
                        this.stages.get(order.stageId).orderCount++;
                        countedOrders.add(order.id);
                    }
                    // second filter, if a stage is selected the order must be in.
                    return !this.selectedStageId || order.stageId === this.selectedStageId;
                });
            })
            .sort((a, b) => {
                const stageA = stages.get(a.stageId);
                const stageB = stages.get(b.stageId);
                const stageDiff = stageA.sequence - stageB.sequence || stageA.id - stageB.id; // sort by stage

                if (stageDiff) {
                    return stageDiff;
                }

                // within the stage, keep the default order unless the state is done then show most recent first.
                let difference;
                if (stageA.id === this.lastStage.id) {
                    difference =
                        deserializeDateTime(b.lastStageChange).ts -
                        deserializeDateTime(a.lastStageChange).ts;
                } else {
                    difference =
                        deserializeDateTime(a.lastStageChange).ts -
                        deserializeDateTime(b.lastStageChange).ts;
                }

                return difference;
            });

        this.filteredOrders = ordersToDisplay;
    }

    get lastStage() {
        return [...this.stages.values()][this.stages.size - 1];
    }

    get firstStage() {
        return [...this.stages.values()][0];
    }

    selectStage(stageId) {
        this.selectedStageId = stageId;
        this.filterOrders();
    }

    async doneOrders(orders) {
        await this.orm.call(
            "pos_preparation_display.order",
            "done_orders_stage",
            [orders.map((order) => order.id), this.id],
            {}
        );
        this.clearPreviousStageHistory(orders.map((order) => order.id));
        this.filterOrders();
    }

    clearPreviousStageHistory(orderIds) {
        for (const stage of this.stages.values()) {
            stage.recallIdsHistory = stage.recallIdsHistory.filter(
                (orderId) => !orderIds.includes(orderId)
            );
        }
    }

    orderNextStage(stageId, direction = 1) {
        if (stageId === this.lastStage.id && direction === 1) {
            return this.firstStage;
        }

        const stages = [...this.stages.values()];
        const currentStagesIdx = stages.findIndex((stage) => stage.id === stageId);

        return stages[currentStagesIdx + direction] ?? false;
    }

    async changeOrderStage(order, force = false, direction = 1, animationTime = 250) {
        const linesVisibility = this.getOrderlinesVisibility(order);

        if (force) {
            for (const orderline of linesVisibility.visible) {
                orderline.todo = false;
            }
        }

        for (const orderline of order.orderlines) {
            if (orderline.todo) {
                this.syncOrderlinesStatus(order);
                break;
            }
        }

        const allOrderlineDone = order.orderlines.every((orderline) => !orderline.todo);
        if (allOrderlineDone) {
            const currentStage = this.stages.get(order.stageId);
            let nextStage = this.orderNextStage(order.stageId, direction);

            const allOrderlineCancelled = order.orderlines.every(
                (orderline) => orderline.productQuantity - orderline.productCancelled === 0
            );

            if (allOrderlineCancelled) {
                nextStage = this.lastStage;
            }

            order.changeStageTimeout = setTimeout(async () => {
                order.lastStageChange = await this.orm.call(
                    "pos_preparation_display.order",
                    "change_order_stage",
                    [[order.id], nextStage.id, this.id],
                    {}
                );
                order.stageId = nextStage.id;
                if (direction === 1) {
                    currentStage.addOrderToRecallHistory(order.id);
                }
                this.resetOrderlineStatus(order, false, true);
                order.clearChangeTimeout();
                this.filterOrders();
            }, animationTime);
        }
    }

    async sendStrickedLineToNextStage(order, orderline) {
        const currentStage = this.stages.get(order.stageId);
        const strickedLine = order.orderlines.filter((l) => !l.todo);

        if (strickedLine.length === 0) {
            await this.changeOrderStage(order, true);
            return;
        }

        const idNewOrder = await this.orm.call(
            "pos_preparation_display.orderline",
            "send_stricked_line_to_next_stage",
            [strickedLine.map((l) => l.id), this.id],
            {}
        );
        currentStage.addOrderToRecallHistory(idNewOrder);
    }

    async getOrders() {
        this.rawData.orders = await this.orm.call(
            "pos_preparation_display.order",
            "get_preparation_display_order",
            [[], this.id],
            {}
        );

        this.processOrders();
    }

    processCategories() {
        this.categories = Object.fromEntries(
            this.rawData.categories
                .map((category) => [category.id, new Category(category)])
                .sort((a, b) => a.sequence - b.sequence)
        );
    }

    processStages() {
        this.selectStage(this.rawData.stages[0].id);
        this.stages = new Map(
            this.rawData.stages.map((stage) => [stage.id, new Stage(stage, this)])
        );
    }

    processOrders() {
        this.stages.forEach((stage) => (stage.orders = []));

        for (const index in this.categories) {
            this.categories[index].orderlines = [];
        }

        this.orders = this.rawData.orders.reduce((orders, order) => {
            if (order.stage_id === null) {
                order.stage_id = this.firstStage.id;
            }

            const orderObj = new Order(order);

            orderObj.orderlines = order.orderlines.map((line) => {
                let blinking = false;

                if (this.noteByLines[line.id] && line.internal_note !== this.noteByLines[line.id]) {
                    blinking = true;
                    this.env.services.sound.play("bell");
                }

                const orderline = new Orderline(line, orderObj, blinking);
                const product = new Product([orderline.productId, orderline.productName]);

                this.noteByLines[line.id] = line.internal_note;
                this.products[product.id] = product;
                this.orderlines[orderline.id] = orderline;
                orderline.productCategoryIds.forEach((categoryId) => {
                    this.categories[categoryId]?.orderlines?.push(orderline);
                    this.categories[categoryId]?.productIds?.add(orderline.productId);
                });

                return orderline;
            });

            if (orderObj.orderlines.length > 0) {
                orders[order.id] = orderObj;
            }

            return orders;
        }, {});

        this.filterOrders();
        return this.orders;
    }

    wsChangeLinesStatus(linesStatus) {
        for (const status of linesStatus) {
            if (!this.orderlines[status.id]) {
                continue;
            }

            this.orderlines[status.id].todo = status.todo;
        }
    }

    wsMoveToNextStage(orderId, stageId, lastStageChange) {
        const order = this.orders[orderId];
        clearTimeout(order.changeStageTimeout);

        order.stageId = stageId;
        order.lastStageChange = lastStageChange;
        this.resetOrderlineStatus(order, false, true);
        this.filterOrders();
    }

    toggleCategory(category) {
        const categoryId = category.id;

        if (this.selectedCategories.has(categoryId)) {
            this.selectedCategories.delete(categoryId);
        } else {
            this.selectedCategories.add(categoryId);

            if (category) {
                category.productIds.forEach((productId) => this.selectedProducts.delete(productId));
            }
        }

        this.filterOrders();
        this.saveFilterToLocalStorage();
    }

    toggleProduct(product) {
        const productId = product.id;
        const category = this.categories[product.categoryId];

        if (this.selectedProducts.has(productId)) {
            this.selectedProducts.delete(productId);
        } else {
            this.selectedProducts.add(productId);

            if (category) {
                this.selectedCategories.delete(category.id);
            }
        }

        this.filterOrders();
        this.saveFilterToLocalStorage();
    }

    async resetOrders() {
        this.orders = {};
        this.rawData.orders = await this.orm.call(
            "pos_preparation_display.display",
            "reset",
            [[this.id]],
            {}
        );
    }

    saveFilterToLocalStorage() {
        const userService = this.env.services.user;
        const localStorageName = `preparation_display_${this.id}.db_${userService.db.name}.user_${userService.userId}`;

        localStorage.setItem(
            localStorageName,
            JSON.stringify({
                products: Array.from(this.selectedProducts),
                categories: Array.from(this.selectedCategories),
            })
        );
    }

    restoreFilterFromLocalStorage() {
        const userService = this.env.services.user;
        const localStorageName = `preparation_display_${this.id}.db_${userService.db.name}.user_${userService.userId}`;
        const localStorageData = JSON.parse(localStorage.getItem(localStorageName));

        if (localStorageData) {
            this.selectedCategories = new Set(localStorageData.categories);
            this.selectedProducts = new Set(localStorageData.products);
        }
    }

    async syncOrderlinesStatus(order) {
        const orderlinesStatus = {};
        const orderlineIds = [];

        for (const orderline of order.orderlines) {
            orderlineIds.push(orderline.id);
            orderlinesStatus[orderline.id] = orderline.todo;
        }

        await this.orm.call(
            "pos_preparation_display.orderline",
            "change_line_status",
            [orderlineIds, orderlinesStatus],
            {}
        );
    }

    resetOrderlineStatus(order, sync = false, all = false) {
        if (order.stageId === this.lastStage.id) {
            return;
        }
        for (const orderline of order.orderlines) {
            if (
                orderline.productQuantity - orderline.productCancelled !== 0 &&
                (this.checkOrderlineVisibility(orderline) || all)
            ) {
                orderline.todo = true;
            }
        }

        if (sync) {
            this.syncOrderlinesStatus(order);
        }
    }

    checkOrderlineVisibility(orderline) {
        const selectedCategories = this.selectedCategories;
        const selectedProducts = this.selectedProducts;
        return (
            orderline.productCategoryIds.some((categoryId) => selectedCategories.has(categoryId)) ||
            selectedProducts.has(orderline.productId) ||
            (selectedCategories.size === 0 && selectedProducts.size === 0)
        );
    }

    getOrderlinesVisibility(order) {
        const orderlines = {
            visible: [],
            visibleTodo: 0,
        };

        for (const orderline of order.orderlines) {
            if (this.checkOrderlineVisibility(orderline)) {
                orderlines.visible.push(orderline);
                orderlines.visibleTodo += orderline.todo ? 1 : 0;
            }
        }

        return orderlines;
    }

    async loadPosHasProducts() {
        return await this.orm.call(
            "pos_preparation_display.display",
            "pos_has_valid_product",
            [],
            {}
        );
    }

    async loadDemoDataProducts() {
        this.loadingProducts = true;
        try {
            // The load_product_frontend will load every products, categories and orders of the onboarding data in the backend.
            // The orders will create preparation_display orders that will be loaded by the preparation display through websocket message.
            // This message is send thanks through a call to _send_orders_to_preparation_display in the onboarding files.
            this.rawData.categories = await this.orm.call(
                "pos_preparation_display.display",
                "load_product_frontend",
                [this.id],
                {}
            );
            this.processCategories();
            this.posHasProducts = await this.loadPosHasProducts();
        } catch (e) {
            if (e instanceof ConnectionLostError) {
                Promise.reject(e);
                return e;
            } else {
                throw e;
            }
        } finally {
            this.loadingProducts = false;
        }
    }

    exit() {
        window.location.href = "/web#action=pos_preparation_display.action_preparation_display";
    }
}
